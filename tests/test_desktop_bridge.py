from __future__ import annotations

import threading
from types import SimpleNamespace

from desktop_app.bridge import DesktopApi


def test_desktop_api_auto_saves_pdf_and_avoids_overwrite(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"pdf")
    jobs = {"job-1": SimpleNamespace(output_pdf=source, report_xlsx=None)}
    api = DesktopApi(jobs, threading.Lock(), downloads_dir=tmp_path / "Downloads")

    first = api.save_job_file("job-1", "pdf")
    second = api.save_job_file("job-1", "pdf")

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["path"] != second["path"]
    assert (tmp_path / "Downloads" / "StampBOX" / "source.pdf").read_bytes() == b"pdf"


def test_desktop_api_rejects_unknown_output_kind(tmp_path):
    api = DesktopApi({}, threading.Lock(), downloads_dir=tmp_path)

    result = api.save_job_file("missing", "archive")

    assert result["ok"] is False
    assert "Unsupported output type" in result["error"]
