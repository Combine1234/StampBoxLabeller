from __future__ import annotations

import csv
import difflib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

DEFAULT_MAPPING_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Tyggl_WZdE0poWozkw4vW8J7BxmsWk1mVvAbmJUQtq8"
    "/export?format=csv&gid=0"
)

PRODUCT_HEADER = "\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
VARIANT_HEADER = "\u0e15\u0e31\u0e27\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
CODE_HEADER = (
    "\u0e42\u0e04\u0e49\u0e14\u0e0a\u0e37\u0e48\u0e2d"
    "\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 + \u0e2a\u0e35"
)


@dataclass(slots=True)
class ProductMappingRow:
    product_name: str
    variant: str
    code: str
    row_text: str = ""


@dataclass(slots=True)
class ProductMappingMatch:
    code: str | None
    score: float
    row: ProductMappingRow | None = None


def google_sheet_csv_url(url: str) -> str:
    if "/export?" in url:
        return url
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return url
    return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv&gid=0"


def _read_text(source: str | Path) -> str:
    source_text = str(source)
    if source_text.startswith(("http://", "https://")):
        with urlopen(google_sheet_csv_url(source_text), timeout=30) as response:
            return response.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def load_product_mapping(source: str | Path | None = None) -> list[ProductMappingRow]:
    csv_text = _read_text(source or DEFAULT_MAPPING_URL)
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return []

    fieldnames = [field.strip() for field in reader.fieldnames]
    product_key = _find_header(fieldnames, [PRODUCT_HEADER], fallback_index=0)
    variant_key = _find_header(fieldnames, [VARIANT_HEADER], fallback_index=2)
    code_key = _find_header(fieldnames, [CODE_HEADER], fallback_index=2)

    rows: list[ProductMappingRow] = []
    for raw in reader:
        product_name = str(raw.get(product_key, "") or "").strip()
        variant = str(raw.get(variant_key, "") or "").strip()
        code = str(raw.get(code_key, "") or "").strip()
        if product_name and code:
            rows.append(
                ProductMappingRow(
                    product_name=product_name,
                    variant=variant,
                    code=code,
                    row_text=" ".join(str(value or "") for value in raw.values()),
                )
            )
    return rows


def _find_header(fieldnames: list[str], candidates: Iterable[str], fallback_index: int) -> str:
    normalized_candidates = {_normalize_header(candidate) for candidate in candidates}
    for field in fieldnames:
        if _normalize_header(field) in normalized_candidates:
            return field
    return fieldnames[min(fallback_index, len(fieldnames) - 1)]


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def normalize_match_text(value: str) -> str:
    value = value.lower()
    value = value.replace("goodhome", "").replace("sogoods", "")
    value = re.sub(r"p\d{4,}", " ", value)
    value = re.sub(r"[\W_]+", "", value, flags=re.UNICODE)
    return value


def _contains_score(shorter: str, longer: str) -> float:
    if not shorter or not longer:
        return 0.0
    if shorter in longer:
        return min(1.0, 0.72 + (len(shorter) / max(len(longer), 1)) * 0.28)
    return 0.0


def _text_score(left: str, right: str) -> float:
    left_norm = normalize_match_text(left)
    right_norm = normalize_match_text(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    contains = max(_contains_score(left_norm, right_norm), _contains_score(right_norm, left_norm))
    ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(contains, ratio)


def find_product_code(
    product_name: str,
    variant: str,
    mapping_rows: list[ProductMappingRow],
    min_score: float = 0.58,
) -> ProductMappingMatch:
    best = ProductMappingMatch(code=None, score=0.0, row=None)
    for row in mapping_rows:
        product_score = _text_score(product_name, row.product_name)
        variant_score = _text_score(variant, row.variant)
        row_score = _text_score(f"{product_name} {variant}", row.row_text)
        combined_score = max((product_score * 0.72) + (variant_score * 0.28), row_score)
        if variant and row.variant and normalize_match_text(variant) in normalize_match_text(row.variant):
            combined_score = max(combined_score, product_score * 0.85 + 0.15)
        if combined_score > best.score:
            best = ProductMappingMatch(code=row.code, score=combined_score, row=row)

    if best.score < min_score:
        return ProductMappingMatch(code=None, score=best.score, row=best.row)
    return best
