from __future__ import annotations

from src.product_mapping import find_product_code, load_product_mapping


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
