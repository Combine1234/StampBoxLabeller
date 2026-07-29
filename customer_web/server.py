from __future__ import annotations

import cgi
import json
import mimetypes
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.overlay_writer import create_output_pdf, locate_font
from src.pdf_product_extractor import build_rows_from_pdf
from src.preview import render_page
from src.product_mapping import DEFAULT_MAPPING_URL
from src.report import report_to_excel_bytes
from src.stamp_guard import is_stampbox_output_pdf, looks_like_stampbox_output_name

LOCKED_MAPPING_URL = DEFAULT_MAPPING_URL
MAX_UPLOAD_BYTES = int(os.environ.get("STAMPBOX_MAX_UPLOAD_MB", "35")) * 1024 * 1024
JOB_RETENTION_SECONDS = int(os.environ.get("STAMPBOX_JOB_RETENTION_SECONDS", "900"))
ERROR_RETENTION_SECONDS = int(os.environ.get("STAMPBOX_ERROR_RETENTION_SECONDS", "180"))


@dataclass
class Job:
    id: str
    original_name: str
    percent: int = 0
    phase: str = "รอเริ่มทำงาน"
    status: str = "queued"
    written: int = 0
    failed: int = 0
    total: int = 0
    error: str = ""
    output_pdf: Path | None = None
    report_xlsx: Path | None = None
    preview_png: Path | None = None
    temp_dir: Path | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported type: {type(value)!r}")


def _safe_output_stem(filename: str) -> str:
    stem = Path(filename).stem.strip() or "shopee_labels"
    cleaned = "".join(char if char.isalnum() or char in (" ", "-", "_") else "_" for char in stem).strip()
    return cleaned or "shopee_labels"


def _download_content_disposition(filename: str) -> str:
    ascii_name = "".join(
        char if char.isascii() and (char.isalnum() or char in (" ", "-", "_", ".")) else "_"
        for char in filename
    ).strip(" .")
    ascii_name = ascii_name or "stampbox.pdf"
    utf8_name = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}"


def _set_job(job_id: str, **updates) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        for key, value in updates.items():
            setattr(job, key, value)
        job.updated_at = time.time()


def _log_job(job_id: str, message: str, **extra) -> None:
    details = " ".join(f"{key}={value}" for key, value in extra.items())
    suffix = f" {details}" if details else ""
    print(f"[stampbox:{job_id}] {message}{suffix}", flush=True)


def _schedule_job_cleanup(job_id: str, delay_seconds: int) -> None:
    timer = threading.Timer(delay_seconds, _cleanup_job, args=(job_id,))
    timer.daemon = True
    timer.start()


def _cleanup_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS.pop(job_id, None)
    if not job:
        return
    temp_dir = job.temp_dir
    if temp_dir and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    _log_job(job_id, "cleaned up")


def _job_payload(job: Job) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "percent": job.percent,
        "phase": job.phase,
        "written": job.written,
        "failed": job.failed,
        "total": job.total,
        "error": job.error,
        "download_url": f"/api/jobs/{job.id}/download" if job.output_pdf else "",
        "report_url": f"/api/jobs/{job.id}/report" if job.report_xlsx else "",
        "preview_url": f"/api/jobs/{job.id}/preview" if job.preview_png else "",
        "file_name": job.output_pdf.name if job.output_pdf else "",
        "updated_at": job.updated_at,
    }


def _status_counts(report_rows: list[dict]) -> tuple[int, int, int]:
    active_rows = [row for row in report_rows if int(row.get("page") or 0) > 0]
    written = sum(1 for row in active_rows if row.get("status") == "WRITTEN")
    failed = sum(1 for row in active_rows if row.get("status") not in {"WRITTEN", "MATCHED"})
    return written, failed, len(active_rows)


def _process_job(job_id: str, input_pdf: Path) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        original_name = job.original_name

    try:
        started_at = time.perf_counter()
        _log_job(job_id, "started", file=original_name, size=input_pdf.stat().st_size)
        _set_job(job_id, status="running", percent=8, phase="รับไฟล์แล้ว")

        _set_job(job_id, percent=22, phase="อ่านรายการสินค้า")
        rows = build_rows_from_pdf(input_pdf, mapping_source=LOCKED_MAPPING_URL)
        _log_job(job_id, "pdf rows extracted", rows=len(rows), seconds=round(time.perf_counter() - started_at, 2))

        _set_job(job_id, percent=48, phase="จับคู่โค้ดสินค้าจาก Sheet")
        font_path = locate_font()
        if not font_path:
            raise RuntimeError("ไม่พบฟอนต์ภาษาไทยในเครื่อง")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = _safe_output_stem(original_name)
        output_dir = input_pdf.parent
        output_pdf = output_dir / f"{stem}_พร้อมส่งลูกค้า_{timestamp}.pdf"
        report_xlsx = output_dir / f"{stem}_report_{timestamp}.xlsx"
        preview_png = output_dir / f"{stem}_preview_{timestamp}.png"

        _set_job(job_id, percent=68, phase="เขียนโค้ดลงใบปะหน้า")
        report_rows = create_output_pdf(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            excel_rows=rows,
            font_path=font_path,
        )
        written, failed, total = _status_counts(report_rows)
        _log_job(
            job_id,
            "overlay written",
            written=written,
            failed=failed,
            total=total,
            seconds=round(time.perf_counter() - started_at, 2),
        )

        _set_job(job_id, percent=88, phase="เตรียมไฟล์บันทึก")
        report_xlsx.write_bytes(report_to_excel_bytes(report_rows))
        preview_png.write_bytes(render_page(output_pdf, page_index=0, zoom=1.7))
        input_pdf.unlink(missing_ok=True)
        _log_job(job_id, "finished", seconds=round(time.perf_counter() - started_at, 2))

        _set_job(
            job_id,
            status="done",
            percent=100,
            phase="เสร็จแล้ว",
            written=written,
            failed=failed,
            total=total,
            output_pdf=output_pdf,
            report_xlsx=report_xlsx,
            preview_png=preview_png,
        )
        _schedule_job_cleanup(job_id, JOB_RETENTION_SECONDS)
    except Exception as exc:
        traceback.print_exc()
        _log_job(job_id, "failed", error=repr(exc))
        input_pdf.unlink(missing_ok=True)
        _set_job(
            job_id,
            status="error",
            percent=100,
            phase="ทำงานไม่สำเร็จ",
            error=f"{type(exc).__name__}: {exc}",
        )
        _schedule_job_cleanup(job_id, ERROR_RETENTION_SECONDS)


class CustomerWebHandler(BaseHTTPRequestHandler):
    server_version = "StampBOX/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _send_bytes(
        self,
        data: bytes,
        content_type: str,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        self._send_bytes(data, "application/json; charset=utf-8", status=status)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status=status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/":
            return self._serve_static("index.html")
        if path.startswith("/static/"):
            return self._serve_static(path.removeprefix("/static/"))
        if path.startswith("/api/jobs/"):
            return self._serve_job_endpoint(path)
        return self._send_error_json("Not found", status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            return self._create_job()
        return self._send_error_json("Not found", status=404)

    def _serve_static(self, relative_path: str) -> None:
        target = (STATIC_DIR / relative_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            return self._send_error_json("Not found", status=404)
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send_bytes(target.read_bytes(), content_type)

    def _create_job(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self._send_error_json("ต้องอัปโหลดไฟล์ PDF")

        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length > MAX_UPLOAD_BYTES:
            max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
            return self._send_error_json(f"ไฟล์ใหญ่เกิน {max_mb}MB กรุณาแบ่ง PDF เป็นชุดเล็กลง", status=413)

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )
        if "pdf" not in form:
            return self._send_error_json("ไม่พบไฟล์ PDF")

        file_item = form["pdf"]
        filename = Path(file_item.filename or "labels.pdf").name
        if not filename.lower().endswith(".pdf"):
            return self._send_error_json("รองรับเฉพาะไฟล์ PDF")
        if looks_like_stampbox_output_name(filename):
            return self._send_error_json(
                "PDF นี้เคยเขียนโค้ดแล้ว กรุณาเลือกไฟล์ PDF ต้นฉบับ",
                status=409,
            )

        job_id = uuid.uuid4().hex
        temp_dir = Path(tempfile.mkdtemp(prefix=f"shopee_job_{job_id}_"))
        input_pdf = temp_dir / "input.pdf"
        input_pdf.write_bytes(file_item.file.read())
        if input_pdf.stat().st_size == 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return self._send_error_json("ไฟล์ PDF ว่างหรืออัปโหลดไม่ครบ")
        try:
            already_processed = is_stampbox_output_pdf(input_pdf, filename)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return self._send_error_json("ไม่สามารถเปิดไฟล์ PDF นี้ได้ กรุณาตรวจสอบไฟล์แล้วลองใหม่")
        if already_processed:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return self._send_error_json(
                "PDF นี้เคยเขียนโค้ดแล้ว กรุณาเลือกไฟล์ PDF ต้นฉบับ",
                status=409,
            )

        with JOBS_LOCK:
            JOBS[job_id] = Job(
                id=job_id,
                original_name=filename,
                percent=3,
                phase="กำลังอัปโหลด",
                temp_dir=temp_dir,
            )

        thread = threading.Thread(target=_process_job, args=(job_id, input_pdf), daemon=True)
        thread.start()
        self._send_json({"job_id": job_id})

    def _serve_job_endpoint(self, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        if len(parts) < 3:
            return self._send_error_json("Not found", status=404)
        job_id = parts[2]
        action = parts[3] if len(parts) > 3 else "status"

        with JOBS_LOCK:
            job = JOBS.get(job_id)
            payload = _job_payload(job) if job else None

        if job is None or payload is None:
            return self._send_error_json(
                "ไม่พบงานนี้แล้ว อาจเป็นเพราะ Render เพิ่งรีสตาร์ทระหว่างทำไฟล์ กรุณาอัปโหลดใหม่อีกครั้ง",
                status=404,
            )
        if action == "status":
            return self._send_json(payload)
        if action == "download":
            return self._send_file(job.output_pdf, "application/pdf", job.output_pdf.name if job.output_pdf else "")
        if action == "report":
            return self._send_file(
                job.report_xlsx,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                job.report_xlsx.name if job.report_xlsx else "",
            )
        if action == "preview":
            return self._send_file(job.preview_png, "image/png", job.preview_png.name if job.preview_png else "")
        return self._send_error_json("Not found", status=404)

    def _send_file(self, path: Path | None, content_type: str, filename: str) -> None:
        if path is None or not path.exists():
            return self._send_error_json("ไฟล์ยังไม่พร้อม", status=404)
        headers = {"Content-Disposition": _download_content_disposition(filename)}
        if content_type == "image/png":
            headers = {}
        self._send_bytes(path.read_bytes(), content_type, headers=headers)


def run(host: str | None = None, port: int | None = None) -> None:
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", "8600"))
    server = ThreadingHTTPServer((host, port), CustomerWebHandler)
    local_url = f"http://127.0.0.1:{port}"
    print(f"StampBOX is running on {host}:{port}")
    print(f"Local URL: {local_url}")
    server.serve_forever()


if __name__ == "__main__":
    run()
