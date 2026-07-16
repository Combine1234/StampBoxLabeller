from __future__ import annotations

import fitz

from src.layout_detector import get_product_area, ratio_rect
from src.pdf_reader import extract_order_no, extract_tracking_no, split_page_into_labels


def test_extract_order_no() -> None:
    assert extract_order_no("Shopee Order No. 2607060SXN316F") == "2607060SXN316F"


def test_split_page_into_nine_labels() -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    labels = split_page_into_labels(page)

    assert len(labels) == 9
    assert labels[0] == fitz.Rect(0, 0, 204, 264)
    assert labels[-1] == fitz.Rect(408, 528, 612, 792)
    doc.close()


def _write_label_markers(page: fitz.Page, rect: fitz.Rect, order: str, tracking: str) -> None:
    page.insert_text((rect.x0 + 8, rect.y0 + 12), "Shopee")
    page.insert_text((rect.x1 - 56, rect.y0 + 12), "PICK UP")
    page.insert_text((rect.x0 + 8, rect.y0 + 34), tracking)
    page.insert_text((rect.x0 + 8, rect.y1 - 16), f"Shopee Order No. {order}")


def test_auto_split_detects_four_up_labels() -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    for index, rect in enumerate(split_page_into_labels(page, rows=2, columns=2), start=1):
        _write_label_markers(page, rect, f"ORDER{index:02d}", f"59105528651380{index:02d}")

    labels = split_page_into_labels(page, rows="auto", columns="auto")

    assert len(labels) == 4
    assert labels[0] == fitz.Rect(0, 0, 200, 200)
    assert labels[-1] == fitz.Rect(200, 200, 400, 400)
    doc.close()


def test_auto_split_detects_two_horizontal_labels() -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    for index, rect in enumerate(split_page_into_labels(page, rows=1, columns=2), start=1):
        _write_label_markers(page, rect, f"ORDER{index:02d}", f"59105528651380{index:02d}")

    labels = split_page_into_labels(page, rows="auto", columns="auto")

    assert len(labels) == 2
    assert labels[0] == fitz.Rect(0, 0, 200, 200)
    assert labels[1] == fitz.Rect(200, 0, 400, 200)
    doc.close()


def test_auto_split_detects_one_full_page_label() -> None:
    doc = fitz.open()
    page = doc.new_page(width=300, height=420)
    _write_label_markers(page, page.rect, "ORDER01", "5910552865138001")

    labels = split_page_into_labels(page, rows="auto", columns="auto")

    assert labels == [fitz.Rect(0, 0, 300, 420)]
    doc.close()


def test_extract_tracking_no_from_top_of_label() -> None:
    doc = fitz.open()
    page = doc.new_page(width=204, height=264)
    page.insert_text((20, 30), "5910552865138006")

    tracking = extract_tracking_no(page, page.rect)

    assert tracking == "5910552865138006"
    doc.close()


def test_ratio_rect() -> None:
    rect = ratio_rect(fitz.Rect(10, 20, 110, 220), {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.8})

    assert rect == fitz.Rect(20, 60, 100, 180)


def test_product_area_from_config() -> None:
    label = fitz.Rect(0, 0, 200, 300)
    config = {"label": {"product_area": {"x0": 0.1, "y0": 0.5, "x1": 0.9, "y1": 0.8}}}

    assert get_product_area(label, config) == fitz.Rect(20, 150, 180, 240)
