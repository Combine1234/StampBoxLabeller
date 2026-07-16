from __future__ import annotations

from src.pdf_product_extractor import extract_items_from_label_text, product_code_for_item


def test_extract_items_from_label_text() -> None:
    text = "\n".join(
        [
            "#",
            "ชื่อสินค้า",
            "ตัวเลือกสินค้า",
            "จำนวน",
            "1",
            "GOODHOME เก้าอี้เลคเชอร์",
            "เลคเชอร์,น้ำเงิน",
            "4",
            "2",
            "GOODHOME ตู้ลิ้นชัก",
            "3ชั้นมั่งมี",
            "1",
            "3",
            "2607109Y8UT4FR",
            "Shopee Order No.",
        ]
    )

    items = extract_items_from_label_text(text, order_no="2607109Y8UT4FR")

    assert items == [
        {
                "short_product_name": "เก้าอี้เลคเชอร์",
                "variant": "เลคเชอร์,น้ำเงิน",
                "quantity": 4,
        },
        {
            "short_product_name": "ตู้ลิ้นชัก",
            "variant": "3ชั้นมั่งมี",
            "quantity": 1,
        },
    ]


def test_product_code_for_item_uses_keyword_and_variant_token() -> None:
    code = product_code_for_item("GOODHOME เก้าอี้เลคเชอร์", "เลคเชอร์,น้ำเงิน")

    assert code == "LECTURE-NAVY"


def test_product_code_variant_tokens_do_not_come_from_product_name() -> None:
    code = product_code_for_item("ตู้ลิ้นชัก 3-4-5ชั้น", "3ชั้นมั่งมี")

    assert code == "DRAWER-3DR"
