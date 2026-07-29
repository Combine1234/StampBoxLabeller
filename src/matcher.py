from __future__ import annotations

from collections import defaultdict
import re
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
    quantity = clean_scalar(row.get("quantity"))
    expanded_bundle = _expand_bundle_code(product_code, quantity)
    if expanded_bundle:
        return expanded_bundle
    if product_code and quantity:
        return f"{product_code} x{quantity}"
    if product_code:
        return product_code
    return ""


def _quantity_int(value: Any) -> int | None:
    cleaned = clean_scalar(value)
    try:
        number = float(cleaned)
    except (TypeError, ValueError):
        return None
    if not number.is_integer() or number < 0:
        return None
    return int(number)


def _expand_bundle_code(product_code: str, quantity: Any) -> str:
    if "+" not in product_code:
        return ""
    multiplier = _quantity_int(quantity)
    if multiplier is None:
        return ""

    components: list[tuple[str, int, str]] = []
    for raw_part in product_code.split("+"):
        match = re.fullmatch(r"\s*(.+?\D)\s*(\d+)(?:\s+(.+?))?\s*", raw_part)
        if not match:
            return ""
        name = match.group(1).strip()
        count = int(match.group(2))
        suffix = (match.group(3) or "").strip()
        components.append((name, count, suffix))

    if len(components) < 2 or any(suffix for _name, _count, suffix in components[:-1]):
        return ""

    aliases = {"สบาย": "เก้าอี้สบาย"}
    color = components[-1][2]
    pieces = [
        f"{aliases.get(name, name)} {count * multiplier}"
        for name, count, _suffix in components
    ]
    prefix = f"{color}: " if color else ""
    return prefix + " / ".join(pieces)


def _code_variant_parts(product_code: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"\s*([^,]+?)\s*,\s*(.+?)\s*", product_code)
    if not match:
        return None
    return match.group(1), match.group(2)


def _compact_variant_lines(base: str, entries: list[tuple[str, Any]]) -> list[str]:
    quantities: dict[str, int] = {}
    for variant, raw_quantity in entries:
        quantity = _quantity_int(raw_quantity)
        if quantity is None:
            continue
        quantities[variant] = quantities.get(variant, 0) + quantity

    pieces = [f"{variant} {quantity}" for variant, quantity in quantities.items()]
    lines: list[str] = []
    for start in range(0, len(pieces), 3):
        chunk = " / ".join(pieces[start : start + 3])
        lines.append(f"{base} {chunk}" if start == 0 else chunk)
    return lines


def _option_quantity_lines(rows: list[dict[str, Any]]) -> list[str]:
    prepared: list[tuple[dict[str, Any], str, tuple[str, str] | None]] = []
    grouped: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for row in rows:
        product_code = clean_scalar(row.get("product_code"))
        parts = _code_variant_parts(product_code)
        prepared.append((row, product_code, parts))
        if parts:
            grouped[parts[0]].append((parts[1], row.get("quantity")))

    compact_bases = {base for base, entries in grouped.items() if len(entries) >= 2}
    emitted_bases: set[str] = set()
    lines: list[str] = []
    for row, _product_code, parts in prepared:
        if parts and parts[0] in compact_bases:
            base = parts[0]
            if base not in emitted_bases:
                lines.extend(_compact_variant_lines(base, grouped[base]))
                emitted_bases.add(base)
            continue
        line = _option_quantity_line(row)
        if line:
            lines.append(line)
    return lines


def build_overlay_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines = _option_quantity_lines(rows)
    return "\n".join(line for line in lines if line.strip())
