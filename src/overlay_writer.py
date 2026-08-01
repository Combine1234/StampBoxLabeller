from __future__ import annotations

import logging
import os
import re
from html import escape
from pathlib import Path
from typing import Any

import fitz

from .layout_detector import find_safe_overlay_rect, load_layout_config
from .matcher import build_overlay_text, group_excel_rows, match_label
from .pdf_reader import (
    extract_label_text,
    extract_order_no,
    extract_tracking_no,
    extract_tracking_no_from_text,
    split_page_into_labels,
)
from .stamp_guard import mark_stampbox_output
from .validator import (
    STATUS_FAILED,
    STATUS_MATCHED,
    STATUS_NO_SAFE_SPACE,
    STATUS_NOT_FOUND_IN_PDF,
    STATUS_TEXT_TOO_LONG,
    STATUS_WRITTEN,
)

LOGGER = logging.getLogger(__name__)

WINDOWS_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\angsana.ttc",
    r"C:\Windows\Fonts\LeelawUI.ttf",
    r"C:\Windows\Fonts\leelawad.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
)
PROJECT_FONT_CANDIDATES = (
    Path("assets/fonts/AngsanaNew-Regular.ttf"),
    Path("assets/fonts/NotoSansThai-SemiBold.ttf"),
    Path("assets/fonts/Sarabun-Regular.ttf"),
    Path("assets/fonts/NotoSansThai-Regular.ttf"),
)


def locate_font(font_path: str | Path | None = None) -> str | None:
    candidates: list[Path] = []
    if font_path:
        candidates.append(Path(font_path))
    if os.getenv("SHOPEE_LABEL_FONT"):
        candidates.append(Path(os.environ["SHOPEE_LABEL_FONT"]))
    candidates.extend(PROJECT_FONT_CANDIDATES)
    candidates.extend(Path(path) for path in WINDOWS_FONT_CANDIDATES)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate.resolve())
    return None


def _font_sizes(config: dict[str, Any]) -> list[float]:
    text_config = config["text"]
    size = float(text_config["font_size_max"])
    minimum = float(text_config["font_size_min"])
    step = float(text_config["font_size_step"])
    sizes: list[float] = []
    while size >= minimum:
        sizes.append(round(size, 2))
        size -= step
    return sizes


def _hex_color_to_rgb(value: str | tuple[float, float, float] | list[float]) -> tuple[float, float, float]:
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    text = str(value).strip().lstrip("#")
    if len(text) != 6:
        return (0, 0, 0)
    return (
        int(text[0:2], 16) / 255,
        int(text[2:4], 16) / 255,
        int(text[4:6], 16) / 255,
    )


def _rgb_to_hex(color: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel * 255))):02X}" for channel in color)


def _line_width(text: str, font: fitz.Font, font_size: float) -> float:
    return font.text_length(text, fontsize=font_size)


def _line_x(rect: fitz.Rect, line: str, font: fitz.Font, font_size: float, align: int) -> float:
    width = _line_width(line, font, font_size)
    if align == fitz.TEXT_ALIGN_CENTER:
        return rect.x0 + max((rect.width - width) / 2, 0)
    if align == fitz.TEXT_ALIGN_RIGHT:
        return rect.x1 - width
    return rect.x0


def _quantity_value(line: str) -> int | None:
    match = re.search(r"\bx\s*(\d+)\s*$", line, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _quantity_tokens(line: str) -> list[tuple[int, int, int]]:
    tokens: list[tuple[int, int, int]] = []
    pattern = re.compile(
        r"\bx\s*(?P<x_quantity>\d+)|(?<![\w])(?P<plain_quantity>\d+)(?=\s*(?:/|$))",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(line):
        group_name = "x_quantity" if match.group("x_quantity") else "plain_quantity"
        start, end = match.span(0) if group_name == "x_quantity" else match.span(group_name)
        tokens.append((start, end, int(match.group(group_name))))
    return tokens


def _html_overlay_text(text: str, quantity_color_gt: int | None) -> str:
    html_lines: list[str] = []
    for line in text.splitlines():
        tokens = [
            (start, end)
            for start, end, quantity in _quantity_tokens(line)
            if quantity_color_gt is not None and quantity > quantity_color_gt
        ]
        if not tokens:
            html_lines.append(f'<div class="line">{escape(line)}</div>')
            continue

        fragments = ['<div class="line">']
        cursor = 0
        for start, end in tokens:
            fragments.append(escape(line[cursor:start]))
            fragments.append(f'<span class="qty-highlight">{escape(line[start:end])}</span>')
            cursor = end
        fragments.extend((escape(line[cursor:]), "</div>"))
        html_lines.append("".join(fragments))
    return "".join(html_lines)


def _html_align(align: int) -> str:
    if align == fitz.TEXT_ALIGN_CENTER:
        return "center"
    if align == fitz.TEXT_ALIGN_RIGHT:
        return "right"
    return "left"


def _insert_html_overlay(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    font_path: str,
    font_size: float,
    line_height: float,
    align: int,
    color: tuple[float, float, float],
    quantity_color_gt: int | None,
    quantity_color: tuple[float, float, float] | None,
) -> tuple[float, float]:
    font_file = Path(font_path)
    font_weight = 600 if "semibold" in font_file.stem.casefold() else 400
    archive = fitz.Archive(str(font_file.parent))
    css = f"""
    @font-face {{
        font-family: LabelThai;
        src: url({font_file.name});
        font-weight: {font_weight};
    }}
    body {{
        margin: 0;
        padding: 0;
        color: {_rgb_to_hex(color)};
        font-family: LabelThai;
        font-size: {font_size}px;
        font-weight: {font_weight};
        line-height: {line_height};
        text-align: {_html_align(align)};
    }}
    .line {{
        white-space: nowrap;
    }}
    .qty-highlight {{
        color: {_rgb_to_hex(quantity_color or color)};
    }}
    """
    return page.insert_htmlbox(
        rect,
        f"<body>{_html_overlay_text(text, quantity_color_gt)}</body>",
        css=css,
        archive=archive,
        scale_low=1,
        overlay=True,
    )


def write_overlay(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    font_path: str,
    font_sizes: list[float] | None = None,
    line_height: float = 1.1,
    align: int = fitz.TEXT_ALIGN_LEFT,
    color: tuple[float, float, float] = (0, 0, 0),
    quantity_color_gt: int | None = None,
    quantity_color: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    if not text.strip():
        return {"status": STATUS_FAILED, "message": "Overlay text is empty"}

    if not Path(font_path).exists():
        return {"status": STATUS_FAILED, "message": f"Font not found: {font_path}"}

    font_name = "thai_overlay_font"
    page.insert_font(fontname=font_name, fontfile=str(font_path))
    font = fitz.Font(fontfile=str(font_path))
    for size in font_sizes or [8.0, 7.5, 7.0, 6.5, 6.0]:
        if any(_line_width(line, font, size) > rect.width for line in text.splitlines()):
            continue
        remaining_height, scale = _insert_html_overlay(
            page,
            rect,
            text,
            str(font_path),
            size,
            line_height,
            align,
            color,
            quantity_color_gt,
            quantity_color,
        )
        if remaining_height >= 0:
            return {
                "status": STATUS_WRITTEN,
                "message": "Success",
                "font_size": size,
                "remaining_height": remaining_height,
                "scale": scale,
            }

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) >= 4:
        dense_line_height = min(line_height, 1.0)
        lowest_size = min(font_sizes or [6.0])
        dense_sizes = [round(size, 2) for size in [lowest_size - 1, lowest_size - 2]]
        dense_sizes = [size for size in dense_sizes if size >= 4.0]
        for size in dense_sizes:
            if any(_line_width(line, font, size) > rect.width for line in lines):
                continue
            remaining_height, scale = _insert_html_overlay(
                page,
                rect,
                text,
                str(font_path),
                size,
                dense_line_height,
                align,
                color,
                quantity_color_gt,
                quantity_color,
            )
            if remaining_height >= 0:
                return {
                    "status": STATUS_WRITTEN,
                    "message": "Success",
                    "font_size": size,
                    "remaining_height": remaining_height,
                    "scale": scale,
                }

    return {"status": STATUS_TEXT_TOO_LONG, "message": "Text did not fit in safe area"}


def _rect_payload(rect: fitz.Rect | None) -> dict[str, float | None]:
    if rect is None:
        return {"overlay_x0": None, "overlay_y0": None, "overlay_x1": None, "overlay_y1": None}
    return {
        "overlay_x0": round(rect.x0, 2),
        "overlay_y0": round(rect.y0, 2),
        "overlay_x1": round(rect.x1, 2),
        "overlay_y1": round(rect.y1, 2),
    }


def _report_row(
    page_number: int,
    label_index: int,
    global_index: int,
    order_no: str | None,
    tracking_no: str | None,
    status: str,
    message: str,
    overlay_rect: fitz.Rect | None = None,
    font_size: float | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "page": page_number,
        "label_index": label_index,
        "global_index": global_index,
        "order_no": order_no or "",
        "tracking_no": tracking_no or "",
        "status": status,
        "message": message,
        "font_size": font_size,
    }
    row.update(_rect_payload(overlay_rect))
    return row


def create_output_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path | None,
    excel_rows: list[dict[str, Any]],
    font_path: str | Path | None = None,
    config_path: str | Path | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    config = load_layout_config(config_path)
    resolved_font = locate_font(font_path)
    if not dry_run and not resolved_font:
        raise FileNotFoundError(
            "No Thai-capable font found. Set SHOPEE_LABEL_FONT or pass font_path."
        )

    data_index = group_excel_rows(excel_rows)
    seen_row_ids: set[str] = set()
    report_rows: list[dict[str, Any]] = []
    font_sizes = _font_sizes(config)
    line_height = float(config["text"].get("line_height", 1.1))
    align_name = str(config["text"].get("align", "left")).lower()
    align = fitz.TEXT_ALIGN_CENTER if align_name == "center" else fitz.TEXT_ALIGN_LEFT
    text_color = _hex_color_to_rgb(config["text"].get("color", "#000000"))
    quantity_color = _hex_color_to_rgb(
        config["text"].get("quantity_color", config["text"].get("underline_color", "#FF0000"))
    )
    quantity_color_gt = config["text"].get(
        "quantity_color_gt", config["text"].get("underline_quantity_gt")
    )

    doc = fitz.open(input_pdf)
    try:
        global_index = 0
        for page_number, page in enumerate(doc, start=1):
            label_rects = split_page_into_labels(
                page,
                rows=config.get("rows"),
                columns=config.get("columns"),
            )
            for label_index, label_rect in enumerate(label_rects, start=1):
                global_index += 1
                label_text = extract_label_text(page, label_rect)
                order_no = extract_order_no(label_text)
                tracking_no = extract_tracking_no_from_text(label_text) or extract_tracking_no(page, label_rect)
                match = match_label(order_no, tracking_no, data_index)
                status = match.status
                message = match.message
                overlay_rect: fitz.Rect | None = None
                font_size: float | None = None

                if match.rows:
                    seen_row_ids.update(str(row.get("_row_id")) for row in match.rows)
                    overlay_text = build_overlay_text(match.rows)
                    if not overlay_text.strip():
                        status = STATUS_MATCHED
                        message = "Matched label, but no mapped product code to write"
                    else:
                        overlay_rect = find_safe_overlay_rect(page, label_rect, config)
                    if overlay_text.strip() and overlay_rect is None:
                        status = STATUS_NO_SAFE_SPACE
                        message = "No safe empty area in product table"
                    elif overlay_text.strip() and dry_run:
                        status = STATUS_MATCHED
                        message = "Ready to write"
                    elif overlay_text.strip():
                        outcome = write_overlay(
                            page,
                            overlay_rect,
                            overlay_text,
                            str(resolved_font),
                            font_sizes=font_sizes,
                            line_height=line_height,
                            align=align,
                            color=text_color,
                            quantity_color_gt=int(quantity_color_gt)
                            if quantity_color_gt is not None
                            else None,
                            quantity_color=quantity_color,
                        )
                        status = str(outcome["status"])
                        message = str(outcome.get("message", ""))
                        font_size = outcome.get("font_size")

                report_rows.append(
                    _report_row(
                        page_number,
                        label_index,
                        global_index,
                        order_no,
                        tracking_no,
                        status,
                        message,
                        overlay_rect,
                        font_size,
                    )
                )

        for row in data_index.rows:
            row_id = str(row.get("_row_id"))
            if row_id not in seen_row_ids:
                report_rows.append(
                    _report_row(
                        0,
                        0,
                        0,
                        row.get("order_no"),
                        row.get("tracking_no"),
                        STATUS_NOT_FOUND_IN_PDF,
                        "Excel row was not matched to any label",
                    )
                )

        if not dry_run:
            if output_pdf is None:
                raise ValueError("output_pdf is required unless dry_run=True")
            output_path = Path(output_pdf)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mark_stampbox_output(doc)
            doc.save(output_path)
            LOGGER.info("Wrote output PDF to %s", output_path)
    finally:
        doc.close()

    return report_rows


def analyze_pdf(
    input_pdf: str | Path,
    excel_rows: list[dict[str, Any]],
    config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    return create_output_pdf(
        input_pdf=input_pdf,
        output_pdf=None,
        excel_rows=excel_rows,
        config_path=config_path,
        dry_run=True,
    )
