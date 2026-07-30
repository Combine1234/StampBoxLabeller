from __future__ import annotations

import multiprocessing
import os
import platform
import sys
import threading
from pathlib import Path


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[1]


ROOT = resource_root()
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Desktop files stay on the local machine, so larger batches are safe here.
os.environ.setdefault("STAMPBOX_MAX_UPLOAD_MB", "250")
os.environ.setdefault("STAMPBOX_JOB_RETENTION_SECONDS", "3600")

import webview

from customer_web import server as web_server
from desktop_app.bridge import DesktopApi


def run_smoke_test() -> None:
    print(
        f"StampBOX smoke test OK: python={sys.version.split()[0]} "
        f"machine={platform.machine()}",
        flush=True,
    )


def main() -> None:
    web_server.STATIC_DIR = ROOT / "desktop_app" / "static"
    server = web_server.ThreadingHTTPServer(("127.0.0.1", 0), web_server.CustomerWebHandler)
    server.daemon_threads = True
    server_thread = threading.Thread(
        target=server.serve_forever,
        name="stampbox-local-server",
        daemon=True,
    )
    server_thread.start()

    window_holder: dict[str, object] = {}
    api = DesktopApi(
        web_server.JOBS,
        web_server.JOBS_LOCK,
        window_getter=lambda: window_holder.get("window"),
    )
    url = f"http://127.0.0.1:{server.server_address[1]}"
    window = webview.create_window(
        "StampBOX",
        url=url,
        js_api=api,
        width=1180,
        height=820,
        min_size=(900, 660),
        background_color="#eef2f7",
    )
    window_holder["window"] = window

    def shutdown() -> None:
        server.shutdown()
        server.server_close()
        with web_server.JOBS_LOCK:
            job_ids = list(web_server.JOBS)
        for job_id in job_ids:
            web_server._cleanup_job(job_id)

    window.events.closed += shutdown
    webview.start(
        debug=os.environ.get("STAMPBOX_DESKTOP_DEBUG") == "1",
        private_mode=True,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if os.environ.get("STAMPBOX_SMOKE_TEST") == "1":
        run_smoke_test()
    else:
        main()
