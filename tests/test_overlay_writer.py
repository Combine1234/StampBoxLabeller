from __future__ import annotations

from src.overlay_writer import _quantity_tokens, _quantity_value


def test_quantity_value() -> None:
    assert _quantity_value("A มินิ น้ำเงิน x1") == 1
    assert _quantity_value("CHAIR-GRN x6") == 6
    assert _quantity_value("ไม่มีจำนวน") is None


def test_quantity_tokens_support_compact_and_bundle_lines() -> None:
    compact = "แฟนซี ฟ้า 1 / เขียว 2 / เหลือง 3"
    bundle = "ชมพู: โต๊ะกลาง 2 / เก้าอี้สบาย 4"

    assert [quantity for _start, _end, quantity in _quantity_tokens(compact)] == [1, 2, 3]
    assert [quantity for _start, _end, quantity in _quantity_tokens(bundle)] == [2, 4]
