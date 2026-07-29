from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


def default_downloads_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.parent.exists() else Path.home()


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique output filename")


class DesktopApi:
    def __init__(
        self,
        jobs: dict[str, Any],
        jobs_lock: Any,
        *,
        downloads_dir: Path | None = None,
        window_getter: Callable[[], Any] | None = None,
    ) -> None:
        self._jobs = jobs
        self._jobs_lock = jobs_lock
        self._downloads_dir = downloads_dir
        self._window_getter = window_getter
        self._last_saved_dir: Path | None = None

    def _source_for(self, job_id: str, kind: str) -> Path:
        attribute = {
            "pdf": "output_pdf",
            "report": "report_xlsx",
        }.get(kind)
        if attribute is None:
            raise ValueError("Unsupported output type")

        with self._jobs_lock:
            job = self._jobs.get(job_id)
            source = Path(getattr(job, attribute)) if job and getattr(job, attribute, None) else None

        if source is None or not source.is_file():
            raise FileNotFoundError("Output file is not ready")
        return source

    def _automatic_destination(self, source: Path) -> Path:
        base_dir = self._downloads_dir or default_downloads_dir()
        output_dir = base_dir / "StampBOX"
        output_dir.mkdir(parents=True, exist_ok=True)
        return unique_destination(output_dir / source.name)

    def _prompt_destination(self, source: Path) -> Path | None:
        if self._window_getter is None:
            return None

        import webview

        window = self._window_getter()
        if window is None:
            return None

        dialog_type = getattr(webview, "SAVE_DIALOG", None)
        if dialog_type is None:
            dialog_type = webview.FileDialog.SAVE
        file_types = (
            "PDF files (*.pdf)" if source.suffix.lower() == ".pdf" else "Excel files (*.xlsx)",
        )
        selected = window.create_file_dialog(
            dialog_type,
            directory=str(self._last_saved_dir or self._downloads_dir or default_downloads_dir()),
            save_filename=source.name,
            file_types=file_types,
        )
        if not selected:
            return None
        if isinstance(selected, (tuple, list)):
            selected = selected[0]
        return Path(selected)

    def save_job_file(self, job_id: str, kind: str = "pdf", prompt: bool = False) -> dict[str, Any]:
        try:
            source = self._source_for(job_id, kind)
            destination = self._prompt_destination(source) if prompt else self._automatic_destination(source)
            if destination is None:
                return {"ok": False, "cancelled": True}

            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and prompt:
                destination.unlink()
            destination = destination if prompt else unique_destination(destination)
            shutil.copy2(source, destination)
            self._last_saved_dir = destination.parent
            return {
                "ok": True,
                "path": str(destination),
                "name": destination.name,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def open_output_folder(self) -> dict[str, Any]:
        try:
            target = self._last_saved_dir or (self._downloads_dir or default_downloads_dir()) / "StampBOX"
            target.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return {"ok": True, "path": str(target)}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
