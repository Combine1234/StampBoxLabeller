from __future__ import annotations

from src.product_mapping import (
    CODE_HEADER,
    CODE_NAME_HEADER,
    COLOR_HEADER,
    PRODUCT_HEADER,
    VARIANT_HEADER,
    find_product_code,
    load_product_mapping,
)


def test_load_product_mapping_reads_code_header(tmp_path) -> None:
    csv_path = tmp_path / "mapping.csv"
    csv_path.write_text(
        "\ufeff"
        "ชื่อสินค้า,SKU,ตัวเลือกสินค้า,โค้ดชื่อสินค้า + สี\n"
        "GOODHOME ราวเดี่ยว A Mininmal,P00042,สีน้ำเงินNAVYMINIMAL,A มินิ น้ำเงิน\n",
        encoding="utf-8",
    )

    rows = load_product_mapping(csv_path)

    assert len(rows) == 1
    assert rows[0].code == "A มินิ น้ำเงิน"


def test_load_product_mapping_combines_code_name_and_color(tmp_path) -> None:
    csv_path = tmp_path / "separate-code-color.csv"
    csv_path.write_text(
        f"{PRODUCT_HEADER},SKU,{VARIANT_HEADER},{CODE_NAME_HEADER},{COLOR_HEADER}\n"
        "Rack,P00001,Silver,3 Shelf,Silver\n",
        encoding="utf-8",
    )

    rows = load_product_mapping(csv_path)

    assert len(rows) == 1
    assert rows[0].code == "3 Shelf Silver"


def test_load_product_mapping_reads_headerless_rows_and_skips_incomplete_rows(tmp_path) -> None:
    csv_path = tmp_path / "headerless.csv"
    csv_path.write_text(
        "Rack,P00001,Silver,3 Shelf,Silver\n"
        "No code,,Blue\n",
        encoding="utf-8",
    )

    rows = load_product_mapping(csv_path)

    assert len(rows) == 1
    assert rows[0].product_name == "Rack"
    assert rows[0].variant == "Silver"
    assert rows[0].code == "3 Shelf Silver"


def test_combined_code_header_still_takes_priority(tmp_path) -> None:
    csv_path = tmp_path / "combined-code.csv"
    csv_path.write_text(
        f"{PRODUCT_HEADER},{VARIANT_HEADER},{CODE_HEADER},{CODE_NAME_HEADER},{COLOR_HEADER}\n"
        "Rack,Silver,RACK SILVER,ignored,ignored\n",
        encoding="utf-8",
    )

    rows = load_product_mapping(csv_path)

    assert rows[0].code == "RACK SILVER"


def test_find_product_code_matches_product_and_variant(tmp_path) -> None:
    csv_path = tmp_path / "mapping.csv"
    csv_path.write_text(
        "ชื่อสินค้า,SKU,ตัวเลือกสินค้า,โค้ดชื่อสินค้า + สี\n"
        "GOODHOME ราวเดี่ยว A Mininmal รุ่น Aมินิมอล เหล็กชุปสี,P00042,สีน้ำเงินNAVYMINIMAL,A มินิ น้ำเงิน\n",
        encoding="utf-8",
    )
    rows = load_product_mapping(csv_path)

    match = find_product_code("ราวเดี่ยว A Mininmal รุ่น Aมินิมอล เหล็กชุปสี", "สีน้ำเงินNAVYMINIMAL", rows)

    assert match.code == "A มินิ น้ำเงิน"
