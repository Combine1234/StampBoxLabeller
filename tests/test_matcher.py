from __future__ import annotations

from src.matcher import build_overlay_text, group_excel_rows, match_label
from src.validator import STATUS_AMBIGUOUS, STATUS_MATCHED, STATUS_NOT_FOUND_IN_EXCEL


def test_match_prefers_tracking_number() -> None:
    rows = [
        {"order_no": "ORDER1", "tracking_no": "1234567890123456", "variant": "A", "quantity": "1"},
    ]
    index = group_excel_rows(rows)

    result = match_label("OTHER", "1234567890123456", index)

    assert result.status == STATUS_MATCHED
    assert result.rows[0]["order_no"] == "ORDER1"


def test_match_falls_back_to_order_number() -> None:
    rows = [{"order_no": "ORDER1", "tracking_no": "", "variant": "A", "quantity": "1"}]
    index = group_excel_rows(rows)

    result = match_label("ORDER1", None, index)

    assert result.status == STATUS_MATCHED


def test_tracking_with_multiple_orders_is_ambiguous() -> None:
    rows = [
        {"order_no": "ORDER1", "tracking_no": "1234567890123456", "variant": "A", "quantity": "1"},
        {"order_no": "ORDER2", "tracking_no": "1234567890123456", "variant": "B", "quantity": "1"},
    ]
    index = group_excel_rows(rows)

    result = match_label(None, "1234567890123456", index)

    assert result.status == STATUS_AMBIGUOUS


def test_not_found() -> None:
    index = group_excel_rows([])

    result = match_label("ORDER1", None, index)

    assert result.status == STATUS_NOT_FOUND_IN_EXCEL


def test_build_overlay_text_prefers_product_code() -> None:
    text = build_overlay_text(
        [
            {
                "product_code": "TABLE-MAPLE",
                "short_product_name": "This should not be written",
                "variant": "This should not be written",
                "quantity": "1",
                "note": "This should not be written",
            },
            {
                "product_code": "IRON",
                "short_product_name": "This should not be written",
                "variant": "This should not be written",
                "quantity": "2",
                "note": "This should not be written",
            },
        ]
    )

    assert text == "TABLE-MAPLE x1\nIRON x2"


def test_build_overlay_text_falls_back_to_variant() -> None:
    text = build_overlay_text([{"variant": "MAPLE", "quantity": "1"}])

    assert text == "MAPLE x1"

