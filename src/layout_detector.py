from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import fitz

DEFAULT_LAYOUT_CONFIG: dict[str, Any] = {
    "rows": "auto",
    "columns": "auto",
    "label": {
        "product_area": {"x0": 0.06, "y0": 0.62, "x1": 0.94, "y1": 0.90},
        "footer_top_ratio": 0.91,
    },
    "text": {
        "font_size_max": 22.0,
        "font_size_min": 10.0,
        "font_size_step": 1.0,
        "line_height": 1.2,
        "max_lines": 6,
        "align": "center",
        "color": "#0057D9",
        "underline_color": "#FF0000",
        "underline_quantity_gt": 1,
    },
    "safety": {
        "margin": 4.0,
        "min_overlay_height": 24.0,
        "allow_product_area_fallback": True,
        "fallback_area": {"x0": 0.06, "y0": 0.66, "x1": 0.94, "y1": 0.88},
    },
}


def _deep_update(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_layout_config(config_path: str | Path | None = None) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_LAYOUT_CONFIG)
    if config_path is None:
        default_path = Path("config/layout_config.json")
        config_path = default_path if default_path.exists() else None
    if config_path:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            _deep_update(config, json.load(handle))
    return config


def ratio_rect(label_rect: fitz.Rect, ratios: dict[str, float]) -> fitz.Rect:
    width = label_rect.width
    height = label_rect.height
    return fitz.Rect(
        label_rect.x0 + width * float(ratios["x0"]),
        label_rect.y0 + height * float(ratios["y0"]),
        label_rect.x0 + width * float(ratios["x1"]),
        label_rect.y0 + height * float(ratios["y1"]),
    )


def get_product_area(label_rect: fitz.Rect, config: dict[str, Any] | None = None) -> fitz.Rect:
    config = config or DEFAULT_LAYOUT_CONFIG
    return ratio_rect(label_rect, config["label"]["product_area"])


def get_footer_top(label_rect: fitz.Rect, config: dict[str, Any] | None = None) -> float:
    config = config or DEFAULT_LAYOUT_CONFIG
    return label_rect.y0 + label_rect.height * float(config["label"]["footer_top_ratio"])


def get_protected_zones(label_rect: fitz.Rect) -> list[fitz.Rect]:
    x = label_rect.x0
    y = label_rect.y0
    w = label_rect.width
    h = label_rect.height
    return [
        fitz.Rect(x, y, x + w, y + h * 0.40),
        fitz.Rect(x + w * 0.48, y + h * 0.34, x + w, y + h * 0.60),
        fitz.Rect(x, y + h * 0.50, x + w, y + h * 0.57),
        fitz.Rect(x, y + h * 0.90, x + w, y + h),
    ]


def get_text_rects(page: fitz.Page, clip: fitz.Rect) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for word in page.get_text("words", clip=clip):
        x0, y0, x1, y1, text, *_ = word
        if str(text).strip():
            rects.append(fitz.Rect(x0, y0, x1, y1))
    return rects


def rect_intersects_any(
    target: fitz.Rect,
    existing_rects: list[fitz.Rect],
    margin: float = 2.0,
) -> bool:
    expanded = fitz.Rect(
        target.x0 - margin,
        target.y0 - margin,
        target.x1 + margin,
        target.y1 + margin,
    )
    return any(expanded.intersects(rect) for rect in existing_rects)


def find_dynamic_overlay_rect(
    page: fitz.Page,
    product_area: fitz.Rect,
    footer_top: float,
    margin: float = 5.0,
    min_height: float = 24.0,
) -> fitz.Rect | None:
    text_rects = get_text_rects(page, product_area)
    if text_rects:
        top = max(rect.y1 for rect in text_rects) + margin
    else:
        top = product_area.y0 + margin

    bottom = footer_top - margin
    if bottom - top < min_height:
        return None
    return fitz.Rect(product_area.x0 + margin, top, product_area.x1 - margin, bottom)


def find_safe_overlay_rect(
    page: fitz.Page,
    label_rect: fitz.Rect,
    config: dict[str, Any] | None = None,
) -> fitz.Rect | None:
    config = config or DEFAULT_LAYOUT_CONFIG
    margin = float(config["safety"].get("margin", 4.0))
    min_height = float(config["safety"].get("min_overlay_height", 24.0))

    product_area = get_product_area(label_rect, config)
    footer_top = get_footer_top(label_rect, config)
    used_fallback = False
    rect = find_dynamic_overlay_rect(
        page,
        product_area,
        footer_top,
        margin=margin,
        min_height=min_height,
    )
    if rect is None:
        if not config["safety"].get("allow_product_area_fallback", False):
            return None
        rect = ratio_rect(label_rect, config["safety"]["fallback_area"])
        rect = fitz.Rect(rect.x0 + margin, rect.y0 + margin, rect.x1 - margin, rect.y1 - margin)
        used_fallback = True

    if rect_intersects_any(rect, get_protected_zones(label_rect), margin=0):
        return None
    if used_fallback:
        return rect
    if rect_intersects_any(rect, get_text_rects(page, rect), margin=margin):
        return None
    return rect
