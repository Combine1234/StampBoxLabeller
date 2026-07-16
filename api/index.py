from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "vercel_static"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.overlay_writer import create_output_pdf, locate_font
from src.pdf_product_extractor import build_rows_from_pdf
from src.product_mapping import DEFAULT_MAPPING_URL

LOCKED_MAPPING_URL = DEFAULT_MAPPING_URL

app = Flask(__name__)


def _safe_output_name(filename: str) -> str:
    stem = Path(filename).stem.strip() or "shopee_labels"
    cleaned = "".join(char if char.isalnum() or char in (" ", "-", "_") else "_" for char in stem).strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{cleaned or 'shopee_labels'}_stampbox_{timestamp}.pdf"


def _status_counts(report_rows: list[dict]) -> tuple[int, int, int]:
    active_rows = [row for row in report_rows if int(row.get("page") or 0) > 0]
    written = sum(1 for row in active_rows if row.get("status") == "WRITTEN")
    failed = sum(1 for row in active_rows if row.get("status") not in {"WRITTEN", "MATCHED"})
    return written, failed, len(active_rows)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/health")
def health():
    return jsonify({"ok": True, "name": "StampBOX"})


@app.post("/api/process")
def process_pdf():
    uploaded = request.files.get("pdf")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "ไม่พบไฟล์ PDF"}), 400
    if not uploaded.filename.lower().endswith(".pdf"):
        return jsonify({"error": "รองรับเฉพาะไฟล์ PDF"}), 400

    font_path = locate_font()
    if not font_path:
        return jsonify({"error": "ไม่พบฟอนต์ภาษาไทย"}), 500

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        input_pdf = temp_dir / "input.pdf"
        output_pdf = temp_dir / "stampbox_output.pdf"
        uploaded.save(input_pdf)

        rows = build_rows_from_pdf(input_pdf, mapping_source=LOCKED_MAPPING_URL)
        report_rows = create_output_pdf(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            excel_rows=rows,
            font_path=font_path,
        )
        written, failed, total = _status_counts(report_rows)

        response = Response(output_pdf.read_bytes(), mimetype="application/pdf")
        response.headers["Content-Disposition"] = f'attachment; filename="{_safe_output_name(uploaded.filename)}"'
        response.headers["X-Stampbox-Written"] = str(written)
        response.headers["X-Stampbox-Failed"] = str(failed)
        response.headers["X-Stampbox-Total"] = str(total)
        return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8620, debug=False)
