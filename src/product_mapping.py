from __future__ import annotations

import csv
import difflib
import io
import logging
import os
import re
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import certifi

DEFAULT_MAPPING_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Tyggl_WZdE0poWozkw4vW8J7BxmsWk1mVvAbmJUQtq8"
    "/export?format=csv&gid=0"
)
DEFAULT_MAPPING_SHEETS = (
    ("Sheet1", "0"),
    ("Sheet2", "798807419"),
    ("so goods", "99385586"),
)

PRODUCT_HEADER = "\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
VARIANT_HEADER = "\u0e15\u0e31\u0e27\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
CODE_HEADER = (
    "\u0e42\u0e04\u0e49\u0e14\u0e0a\u0e37\u0e48\u0e2d"
    "\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 + \u0e2a\u0e35"
)
CODE_NAME_HEADER = "\u0e42\u0e04\u0e49\u0e14\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
COLOR_HEADER = "\u0e2a\u0e35"


@dataclass(slots=True)
class ProductMappingRow:
    product_name: str
    variant: str
    code: str
    row_text: str = ""
    product_norm: str = ""
    variant_norm: str = ""
    row_norm: str = ""


@dataclass(slots=True)
class ProductMappingMatch:
    code: str | None
    score: float
    row: ProductMappingRow | None = None


_MAPPING_CACHE: dict[str, tuple[float, list[ProductMappingRow]]] = {}
LOGGER = logging.getLogger(__name__)


def google_sheet_csv_url(url: str) -> str:
    if "/export?" in url:
        return url
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return url
    return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv&gid=0"


def default_mapping_tab_urls(url: str = DEFAULT_MAPPING_URL) -> list[tuple[str, str]]:
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return [("mapping", google_sheet_csv_url(url))]
    spreadsheet_id = match.group(1)
    return [
        (
            sheet_name,
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}",
        )
        for sheet_name, gid in DEFAULT_MAPPING_SHEETS
    ]


def _runtime_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[1]


def _bundled_mapping_path() -> Path:
    return _runtime_root() / "config" / "product_mapping_cache.csv"


def _user_mapping_cache_path() -> Path:
    override = os.environ.get("STAMPBOX_MAPPING_CACHE_FILE")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        cache_root = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        cache_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "StampBOX" / "product_mapping.csv"


def _is_default_mapping_source(source: str) -> bool:
    return google_sheet_csv_url(source) == google_sheet_csv_url(DEFAULT_MAPPING_URL)


def _read_url_text(source: str) -> str:
    request = Request(
        google_sheet_csv_url(source),
        headers={"User-Agent": "StampBOX/1.0"},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=30, context=context) as response:
        return response.read().decode("utf-8-sig")


def _read_default_mapping_text(source: str) -> str:
    tab_urls = default_mapping_tab_urls(source)
    with ThreadPoolExecutor(max_workers=len(tab_urls)) as executor:
        csv_texts = list(executor.map(lambda item: _read_url_text(item[1]), tab_urls))

    merged_rows: list[ProductMappingRow] = []
    for (sheet_name, _url), csv_text in zip(tab_urls, csv_texts):
        sheet_rows = _parse_mapping_csv(csv_text)
        LOGGER.info("Loaded %d product mappings from %s", len(sheet_rows), sheet_name)
        merged_rows.extend(sheet_rows)
    return _mapping_rows_to_csv(_deduplicate_mapping_rows(merged_rows))


def _write_user_mapping_cache(csv_text: str) -> None:
    cache_path = _user_mapping_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_suffix(".tmp")
    temp_path.write_text(csv_text, encoding="utf-8")
    temp_path.replace(cache_path)


def _read_default_mapping_fallback() -> str:
    for cache_path in (_user_mapping_cache_path(), _bundled_mapping_path()):
        try:
            if cache_path.is_file():
                LOGGER.warning("Using cached product mapping from %s", cache_path)
                return cache_path.read_text(encoding="utf-8-sig")
        except OSError:
            LOGGER.warning("Could not read product mapping cache at %s", cache_path, exc_info=True)
    raise FileNotFoundError("No cached product mapping is available")


def _read_text(source: str | Path) -> str:
    source_text = str(source)
    if not source_text.startswith(("http://", "https://")):
        return Path(source).read_text(encoding="utf-8-sig")

    if os.environ.get("STAMPBOX_MAPPING_OFFLINE") == "1":
        if not _is_default_mapping_source(source_text):
            raise URLError("Product mapping offline mode is enabled")
        return _read_default_mapping_fallback()

    try:
        csv_text = (
            _read_default_mapping_text(source_text)
            if _is_default_mapping_source(source_text)
            else _read_url_text(source_text)
        )
        if _is_default_mapping_source(source_text):
            try:
                _write_user_mapping_cache(csv_text)
            except OSError:
                LOGGER.warning("Could not update the product mapping cache", exc_info=True)
        return csv_text
    except (OSError, TimeoutError, URLError):
        if not _is_default_mapping_source(source_text):
            raise
        LOGGER.warning("Could not refresh product mapping; using cached data", exc_info=True)
        return _read_default_mapping_fallback()


def load_product_mapping(source: str | Path | None = None) -> list[ProductMappingRow]:
    source_key = str(source or DEFAULT_MAPPING_URL)
    cache_seconds = int(os.environ.get("STAMPBOX_MAPPING_CACHE_SECONDS", "300"))
    if cache_seconds > 0 and source_key in _MAPPING_CACHE:
        cached_at, cached_rows = _MAPPING_CACHE[source_key]
        if time.monotonic() - cached_at <= cache_seconds:
            return cached_rows

    rows = _parse_mapping_csv(_read_text(source_key))
    if cache_seconds > 0:
        _MAPPING_CACHE[source_key] = (time.monotonic(), rows)
    return rows


def _parse_mapping_csv(csv_text: str) -> list[ProductMappingRow]:
    raw_rows = [
        [str(value or "").strip() for value in row]
        for row in csv.reader(io.StringIO(csv_text))
    ]
    nonempty_rows = [row for row in raw_rows if any(row)]
    if not nonempty_rows:
        return []

    header = nonempty_rows[0]
    normalized_header = [_normalize_header(value) for value in header]
    has_header = _normalize_header(PRODUCT_HEADER) in normalized_header
    data_rows = nonempty_rows[1:] if has_header else nonempty_rows

    if has_header:
        product_index = normalized_header.index(_normalize_header(PRODUCT_HEADER))
        variant_index = _header_index(normalized_header, VARIANT_HEADER)
        combined_code_index = _header_index(normalized_header, CODE_HEADER)
        code_name_index = _header_index(normalized_header, CODE_NAME_HEADER)
        color_index = _header_index(normalized_header, COLOR_HEADER)
    else:
        product_index = 0
        variant_index = 2
        combined_code_index = None
        code_name_index = 3
        color_index = 4

    rows: list[ProductMappingRow] = []
    for raw in data_rows:
        product_name = _cell(raw, product_index)
        variant = _cell(raw, variant_index)
        code = _cell(raw, combined_code_index)
        if not code:
            code = " ".join(
                value
                for value in (_cell(raw, code_name_index), _cell(raw, color_index))
                if value
            )
        if not product_name or not code:
            continue
        row_text = " ".join(value for value in raw if value)
        rows.append(
            ProductMappingRow(
                product_name=product_name,
                variant=variant,
                code=code,
                row_text=row_text,
                product_norm=normalize_match_text(product_name),
                variant_norm=normalize_match_text(variant),
                row_norm=normalize_match_text(row_text),
            )
        )
    return rows


def _header_index(normalized_header: list[str], header: str) -> int | None:
    normalized = _normalize_header(header)
    return normalized_header.index(normalized) if normalized in normalized_header else None


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return row[index].strip()


def _deduplicate_mapping_rows(rows: list[ProductMappingRow]) -> list[ProductMappingRow]:
    deduplicated: list[ProductMappingRow] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.product_norm, row.variant_norm, normalize_match_text(row.code))
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(row)
    return deduplicated


def _mapping_rows_to_csv(rows: list[ProductMappingRow]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([PRODUCT_HEADER, VARIANT_HEADER, CODE_HEADER])
    for row in rows:
        writer.writerow([row.product_name, row.variant, row.code])
    return output.getvalue()


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


def _text_score_norm(left_norm: str, right_norm: str, use_ratio: bool = True) -> float:
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    contains = max(_contains_score(left_norm, right_norm), _contains_score(right_norm, left_norm))
    if contains >= 0.95 or not use_ratio:
        return contains
    ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(contains, ratio)


def _text_score(left: str, right: str) -> float:
    return _text_score_norm(normalize_match_text(left), normalize_match_text(right))


def find_product_code(
    product_name: str,
    variant: str,
    mapping_rows: list[ProductMappingRow],
    min_score: float = 0.58,
) -> ProductMappingMatch:
    product_norm = normalize_match_text(product_name)
    variant_norm = normalize_match_text(variant)
    row_query_norm = normalize_match_text(f"{product_name} {variant}")
    best = ProductMappingMatch(code=None, score=0.0, row=None)
    for row in mapping_rows:
        row_product_norm = row.product_norm or normalize_match_text(row.product_name)
        row_variant_norm = row.variant_norm or normalize_match_text(row.variant)
        row_norm = row.row_norm or normalize_match_text(row.row_text)
        product_score = _text_score_norm(product_norm, row_product_norm)
        variant_score = _text_score_norm(variant_norm, row_variant_norm) if variant_norm else 0.0
        row_score = _text_score_norm(row_query_norm, row_norm, use_ratio=False)
        combined_score = max((product_score * 0.72) + (variant_score * 0.28), row_score)
        if variant_norm and row_variant_norm and variant_norm in row_variant_norm:
            combined_score = max(combined_score, product_score * 0.85 + 0.15)
        if combined_score > best.score:
            best = ProductMappingMatch(code=row.code, score=combined_score, row=row)

    if best.score < min_score:
        return ProductMappingMatch(code=None, score=best.score, row=best.row)
    return best
