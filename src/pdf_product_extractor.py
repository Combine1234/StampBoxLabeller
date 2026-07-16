from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fitz

from .layout_detector import load_layout_config
from .pdf_reader import (
    extract_label_text,
    extract_order_no,
    extract_tracking_no,
    split_page_into_labels,
)
from .product_mapping import DEFAULT_MAPPING_URL, find_product_code, load_product_mapping

PDF_TEXT_TRANSLATION = {
    0x00: " ",
    0xF70A: chr(0x0E48),
    0xF70B: chr(0x0E49),
    0xF70C: chr(0x0E4A),
    0xF70E: chr(0x0E4C),
    0x00FF: chr(0x0E19),
    0x0100: chr(0x0E1A),
    0x0101: chr(0x0E1B),
    0x00FE: chr(0x0E18),
    0x00FD: chr(0x0E17),
}

HEADER_WORDS = {
    "#",
    "ชื่อสินค้า",
    "ชื่อสินคา",
    "ตัวเลือกสินค้า",
    "ตัวเลือกสินคา",
    "จำนวน",
    "จํานวน",
    "จำนวนรวม",
    "จํานวนรวม",
}

DEFAULT_CODE_RULES: dict[str, Any] = {
    "rules": [
        {"code": "LECTURE", "keywords": ["เลคเชอร์", "lecture"]},
        {"code": "CHAIR", "keywords": ["เก้าอี้"]},
        {"code": "DRAWER", "keywords": ["ลิ้นชัก", "ตู้"]},
        {"code": "RACK", "keywords": ["ราวเดี่ยว", "ราวตาก"]},
        {"code": "IRON", "keywords": ["โต๊ะรีด"]},
        {"code": "TABLE71", "keywords": ["71x71"]},
        {"code": "JTABLE", "keywords": ["โต๊ะญี่ปุ่น", "75x75"]},
        {"code": "BED", "keywords": ["เปล"]},
    ],
    "variant_tokens": [
        {"token": "BLK", "keywords": ["ดำ", "black"]},
        {"token": "BLU", "keywords": ["ฟ้า"]},
        {"token": "NAVY", "keywords": ["น้ำเงิน", "navy"]},
        {"token": "GRN", "keywords": ["เขียว"]},
        {"token": "YEL", "keywords": ["เหลือง"]},
        {"token": "MAPLE", "keywords": ["เมเปิ้ล"]},
        {"token": "30IN", "keywords": ["30นิ้ว"]},
        {"token": "3DR", "keywords": ["3ชั้น"]},
        {"token": "4DR", "keywords": ["4ชั้น"]},
        {"token": "5DR", "keywords": ["5ชั้น"]},
    ],
}


def clean_pdf_text(value: str) -> str:
    value = value.translate(PDF_TEXT_TRANSLATION)
    value = re.sub(r"([\u0e48\u0e49\u0e4a\u0e4b\u0e4c])([\u0e38\u0e39])", r"\2\1", value)
    value = value.replace(chr(0x0E4D) + chr(0x0E49) + chr(0x0E32), chr(0x0E49) + chr(0x0E33))
    value = value.replace(chr(0x0E4D) + chr(0x0E32), chr(0x0E33))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _is_int(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", clean_pdf_text(value)))


def _is_header(value: str) -> bool:
    return clean_pdf_text(value) in {clean_pdf_text(item) for item in HEADER_WORDS}


def _product_section(lines: list[str], order_no: str | None) -> list[str]:
    cleaned = [clean_pdf_text(line) for line in lines if clean_pdf_text(line)]
    quantity_headers = [index for index, line in enumerate(cleaned) if line in {"จำนวน", "จํานวน"}]
    start = quantity_headers[-1] + 1 if quantity_headers else 0

    section: list[str] = []
    for line in cleaned[start:]:
        if order_no and line == order_no:
            break
        if line == "Shopee Order No.":
            break
        if _is_header(line):
            continue
        section.append(line)

    if section and _is_int(section[-1]):
        section.pop()
    return section


def _split_item_segments(section: list[str]) -> list[list[str]]:
    items: list[list[str]] = []
    index = 0
    expected = 1
    while index < len(section):
        if section[index] == str(expected):
            index += 1
            segment: list[str] = []
            while index < len(section) and section[index] != str(expected + 1):
                segment.append(section[index])
                index += 1
            if segment:
                items.append(segment)
                expected += 1
        else:
            index += 1
    return items


def _parse_segment(segment: list[str]) -> dict[str, Any]:
    body = [clean_pdf_text(value) for value in segment if clean_pdf_text(value)]
    quantity: int | str = 1
    if body and _is_int(body[-1]):
        quantity = int(body.pop())

    variant = ""
    product_name = " ".join(body)
    if len(body) >= 2:
        variant_candidate = body[-1]
        if not variant_candidate.upper().startswith(("GOODHOME", "SOGOODS")):
            variant = variant_candidate
            product_name = " ".join(body[:-1])
    elif body:
        variant = body[0]

    product_name = product_name.replace("GOODHOME", "").replace("SOGOODS", "").strip()
    return {
        "short_product_name": product_name,
        "variant": _compact_variant(variant),
        "quantity": quantity,
    }


def _compact_variant(value: str) -> str:
    variant = clean_pdf_text(value)
    for marker in ("ราวตากผ้าสีพาสเทล ", "มี7สีให้เลือก ", "มี5สีให้เลือก "):
        if marker in variant:
            variant = variant.split(marker)[-1].strip()
    return variant.replace(" ,", ",").replace(", ", ",")


def extract_items_from_label_text(text: str, order_no: str | None = None) -> list[dict[str, Any]]:
    section = _product_section(text.splitlines(), order_no)
    return [_parse_segment(segment) for segment in _split_item_segments(section)]


def load_code_rules(rules_path: str | Path | None = None) -> dict[str, Any]:
    if rules_path is None:
        rules_path = Path("config/product_code_rules.json")
    path = Path(rules_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return DEFAULT_CODE_RULES


def product_code_for_item(
    product_name: str,
    variant: str,
    rules: dict[str, Any] | None = None,
) -> str:
    rules = rules or DEFAULT_CODE_RULES
    haystack = f"{product_name} {variant}".lower()
    base = ""
    for rule in rules.get("rules", []):
        if any(str(keyword).lower() in haystack for keyword in rule.get("keywords", [])):
            base = str(rule.get("code", "")).strip().upper()
            break

    if not base:
        fallback = variant or product_name
        base = re.sub(r"\s+", " ", fallback).strip()[:24].upper()

    tokens: list[str] = []
    variant_haystack = variant.lower()
    for token_rule in rules.get("variant_tokens", []):
        token = str(token_rule.get("token", "")).strip().upper()
        if token and any(str(keyword).lower() in variant_haystack for keyword in token_rule.get("keywords", [])):
            tokens.append(token)

    return "-".join([base, *dict.fromkeys(tokens)])


def build_rows_from_pdf(
    input_pdf: str | Path,
    config_path: str | Path | None = None,
    rules_path: str | Path | None = None,
    mapping_source: str | Path | None = DEFAULT_MAPPING_URL,
) -> list[dict[str, Any]]:
    config = load_layout_config(config_path)
    rules = load_code_rules(rules_path)
    mapping_rows = load_product_mapping(mapping_source) if mapping_source else []
    rows: list[dict[str, Any]] = []

    with fitz.open(input_pdf) as doc:
        for page_number, page in enumerate(doc, start=1):
            labels = split_page_into_labels(
                page,
                rows=config.get("rows"),
                columns=config.get("columns"),
            )
            for label_index, label_rect in enumerate(labels, start=1):
                text = extract_label_text(page, label_rect)
                order_no = extract_order_no(text) or ""
                tracking_no = extract_tracking_no(page, label_rect) or ""
                for item_index, item in enumerate(
                    extract_items_from_label_text(text, order_no=order_no),
                    start=1,
                ):
                    product_name = str(item.get("short_product_name", ""))
                    variant = str(item.get("variant", ""))
                    fallback_code = product_code_for_item(product_name, variant, rules)
                    mapping_match = find_product_code(product_name, variant, mapping_rows) if mapping_rows else None
                    if mapping_match and mapping_match.code:
                        product_code = mapping_match.code
                        note = f"mapped score={mapping_match.score:.2f}"
                    else:
                        product_code = f"(map \u0e44\u0e21\u0e48\u0e1e\u0e1a) {fallback_code}"
                        score = mapping_match.score if mapping_match else 0.0
                        note = f"map_not_found fallback score={score:.2f}"
                    rows.append(
                        {
                            "order_no": order_no,
                            "tracking_no": tracking_no,
                            "product_code": product_code,
                            "short_product_name": product_name,
                            "variant": variant,
                            "quantity": item.get("quantity", 1),
                            "box_no": "",
                            "total_boxes": "",
                            "note": note,
                            "enabled": True,
                            "_source_row": f"pdf-{page_number}-{label_index}-{item_index}",
                        }
                    )
    return rows
