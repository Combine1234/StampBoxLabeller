from __future__ import annotations

from src.overlay_writer import _html_overlay_text, _quantity_tokens, _quantity_value, locate_font


def test_quantity_value() -> None:
    assert _quantity_value("A มินิ น้ำเงิน x1") == 1
    assert _quantity_value("CHAIR-GRN x6") == 6
    assert _quantity_value("ไม่มีจำนวน") is None


def test_quantity_tokens_support_compact_and_bundle_lines() -> None:
    compact = "แฟนซี ฟ้า 1 / เขียว 2 / เหลือง 3"
    bundle = "ชมพู: โต๊ะกลาง 2 / เก้าอี้สบาย 4"

    assert [quantity for _start, _end, quantity in _quantity_tokens(compact)] == [1, 2, 3]
    assert [quantity for _start, _end, quantity in _quantity_tokens(bundle)] == [2, 4]

    x_line = "BAR BLACK x12"
    start, end, quantity = _quantity_tokens(x_line)[0]
    assert x_line[start:end] == "x12"
    assert quantity == 12


def test_quantity_greater_than_one_is_highlighted_without_underline() -> None:
    html = _html_overlay_text("แฟนซี ฟ้า 1 / เขียว 2\nพิง B สีน้ำเงิน x5", 1)

    assert "แฟนซี ฟ้า 1 / เขียว <span class=\"qty-highlight\">2</span>" in html
    assert "<span class=\"qty-highlight\">x5</span>" in html
    assert "underline" not in html


def test_bundled_angsana_new_is_the_default_font() -> None:
    font_path = locate_font()

    assert font_path is not None
    assert font_path.endswith("AngsanaNew-Regular.ttf")
