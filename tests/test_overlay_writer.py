from __future__ import annotations

from src.overlay_writer import _quantity_value


def test_quantity_value() -> None:
    assert _quantity_value("A มินิ น้ำเงิน x1") == 1
    assert _quantity_value("CHAIR-GRN x6") == 6
    assert _quantity_value("ไม่มีจำนวน") is None
