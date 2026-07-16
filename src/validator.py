from __future__ import annotations

import math
from typing import Any, Iterable

STATUS_MATCHED = "MATCHED"
STATUS_NOT_FOUND_IN_EXCEL = "NOT_FOUND_IN_EXCEL"
STATUS_NOT_FOUND_IN_PDF = "NOT_FOUND_IN_PDF"
STATUS_AMBIGUOUS = "AMBIGUOUS"
STATUS_NO_SAFE_SPACE = "NO_SAFE_SPACE"
STATUS_TEXT_TOO_LONG = "TEXT_TOO_LONG"
STATUS_WRITTEN = "WRITTEN"
STATUS_FAILED = "FAILED"

REQUIRED_COLUMNS = ("order_no", "variant", "quantity")
OPTIONAL_COLUMNS = (
    "tracking_no",
    "product_code",
    "short_product_name",
    "box_no",
    "total_boxes",
    "note",
    "enabled",
)
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

FALSE_STRINGS = {"0", "false", "f", "no", "n", "off", "ไม่", "ไม่ใช่", "ปิด"}
TRUE_STRINGS = {"1", "true", "t", "yes", "y", "on", "ใช่", "เปิด"}


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if value != value:
        return True
    return isinstance(value, str) and not value.strip()


def clean_scalar(value: Any) -> str:
    if is_blank(value):
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).strip()
    return str(value).strip()


def enabled_value(value: Any) -> bool:
    if is_blank(value):
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    if normalized in FALSE_STRINGS:
        return False
    if normalized in TRUE_STRINGS:
        return True
    return True


def validate_excel_columns(columns: Iterable[str]) -> list[str]:
    available = {str(column).strip() for column in columns}
    missing = [column for column in REQUIRED_COLUMNS if column not in available]
    return [f"Missing required column: {column}" for column in missing]


def normalize_key(value: Any) -> str:
    return clean_scalar(value).upper().replace(" ", "")


def normalize_row(raw: dict[str, Any], source_row: int | None = None) -> dict[str, Any]:
    row = {column: clean_scalar(raw.get(column, "")) for column in ALL_COLUMNS}
    row["enabled"] = enabled_value(raw.get("enabled", True))
    if source_row is not None:
        row["_source_row"] = source_row
    return row
