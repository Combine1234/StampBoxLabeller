from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import DataIndex, MatchResult
from .validator import (
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_NOT_FOUND_IN_EXCEL,
    clean_scalar,
    normalize_key,
)


def _copy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        new_row = dict(row)
        new_row.setdefault("_row_id", str(new_row.get("_source_row", index)))
        copied.append(new_row)
    return copied


def group_excel_rows(rows: list[dict[str, Any]]) -> DataIndex:
    prepared = _copy_rows(rows)
    by_tracking: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in prepared:
        tracking_key = normalize_key(row.get("tracking_no"))
        order_key = normalize_key(row.get("order_no"))
        if tracking_key:
            by_tracking[tracking_key].append(row)
        if order_key:
            by_order[order_key].append(row)

    return DataIndex(
        by_tracking=dict(by_tracking),
        by_order=dict(by_order),
        rows=prepared,
    )


def _distinct_order_keys(rows: list[dict[str, Any]]) -> set[str]:
    return {normalize_key(row.get("order_no")) for row in rows if normalize_key(row.get("order_no"))}


def _filter_by_order(rows: list[dict[str, Any]], order_no: str | None) -> list[dict[str, Any]]:
    order_key = normalize_key(order_no)
    if not order_key:
        return []
    return [row for row in rows if normalize_key(row.get("order_no")) == order_key]


def match_label(
    order_no: str | None,
    tracking_no: str | None,
    data_index: DataIndex,
) -> MatchResult:
    tracking_key = normalize_key(tracking_no)
    order_key = normalize_key(order_no)

    if tracking_key and tracking_key in data_index.by_tracking:
        rows = data_index.by_tracking[tracking_key]
        distinct_orders = _distinct_order_keys(rows)
        if len(distinct_orders) > 1:
            filtered = _filter_by_order(rows, order_no)
            if filtered:
                return MatchResult(STATUS_MATCHED, filtered, "Matched by tracking and order number")
            return MatchResult(STATUS_AMBIGUOUS, [], "Tracking number maps to multiple order numbers")
        return MatchResult(STATUS_MATCHED, rows, "Matched by tracking number")

    if order_key and order_key in data_index.by_order:
        return MatchResult(STATUS_MATCHED, data_index.by_order[order_key], "Matched by order number")

    if not tracking_key and not order_key:
        return MatchResult(STATUS_NOT_FOUND_IN_EXCEL, [], "No order or tracking number found in label")

    return MatchResult(STATUS_NOT_FOUND_IN_EXCEL, [], "No matching Excel row")


def match_label_to_excel(
    order_no: str | None,
    tracking_no: str | None,
    data_index: DataIndex,
) -> list[dict[str, Any]]:
    return match_label(order_no, tracking_no, data_index).rows


def _option_quantity_line(row: dict[str, Any]) -> str:
    product_code = clean_scalar(row.get("product_code"))
    variant = clean_scalar(row.get("variant"))
    quantity = clean_scalar(row.get("quantity"))
    label = product_code or variant
    if label and quantity:
        return f"{label} x{quantity}"
    if label:
        return label
    if quantity:
        return f"x{quantity}"
    return ""


def _option_quantity_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        line = _option_quantity_line(row)
        if line:
            lines.append(line)
    return lines


def build_overlay_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines = _option_quantity_lines(rows)
    return "\n".join(line for line in lines if line.strip())
