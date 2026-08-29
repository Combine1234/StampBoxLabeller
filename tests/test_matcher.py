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


def test_build_overlay_text_skips_unmapped_product() -> None:
    text = build_overlay_text([{"variant": "MAPLE", "quantity": "1"}])

    assert text == ""


def test_build_overlay_text_multiplies_bundle_components() -> None:
    text = build_overlay_text(
        [{"product_code": "โต๊ะกลาง1+สบาย2 ชมพู", "quantity": 2}]
    )

    assert text == "ชมพู: โต๊ะกลาง 2 / เก้าอี้สบาย 4"


def test_build_overlay_text_does_not_multiply_model_numbers() -> None:
    text = build_overlay_text(
        [{"product_code": "ขาคู่36นิ้ว(ขาขาว)", "quantity": 2}]
    )

    assert text == "ขาคู่36นิ้ว(ขาขาว) x2"


def test_build_overlay_text_compacts_same_product_colors() -> None:
    rows = [
        {"product_code": "แฟนซี, ฟ้า", "quantity": 1},
        {"product_code": "แฟนซี, เขียว", "quantity": 1},
        {"product_code": "แฟนซี, เหลือง", "quantity": 1},
        {"product_code": "แฟนซี, ม่วง", "quantity": 2},
        {"product_code": "แฟนซี, ส้ม", "quantity": 1},
    ]

    assert build_overlay_text(rows) == (
        "แฟนซี ฟ้า 1 / เขียว 1 / เหลือง 1\n"
        "ม่วง 2 / ส้ม 1"
    )
