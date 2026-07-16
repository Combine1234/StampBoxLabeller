from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz


def render_page(pdf_path: str | Path, page_index: int = 0, zoom: float = 1.5) -> bytes:
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")


def render_page_with_report(
    pdf_path: str | Path,
    report_rows: list[dict[str, Any]],
    page_index: int = 0,
    zoom: float = 1.5,
) -> bytes:
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        shape = page.new_shape()
        page_number = page_index + 1
        for row in report_rows:
            if int(row.get("page") or 0) != page_number:
                continue
            coords = [row.get("overlay_x0"), row.get("overlay_y0"), row.get("overlay_x1"), row.get("overlay_y1")]
            if any(value is None or value == "" for value in coords):
                continue
            rect = fitz.Rect(*(float(value) for value in coords))
            status = str(row.get("status", ""))
            color = (0, 0.55, 0) if status in {"MATCHED", "WRITTEN"} else (0.9, 0.2, 0)
            shape.draw_rect(rect)
            shape.finish(color=color, width=1.1)
            page.insert_text(
                (rect.x0, max(rect.y0 - 3, 0)),
                f"{row.get('label_index')}: {status}",
                fontsize=5,
                color=color,
            )
        shape.commit(overlay=True)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")

