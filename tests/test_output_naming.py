from __future__ import annotations

from src.output_naming import edited_pdf_filename


def test_edited_pdf_filename_uses_original_stem() -> None:
    assert edited_pdf_filename("orders.pdf") == "orders_edited.pdf"
    assert edited_pdf_filename("SG Flash - 133 17.7.PDF") == "SG Flash - 133 17.7_edited.pdf"


def test_edited_pdf_filename_sanitizes_unsafe_characters() -> None:
    assert edited_pdf_filename("labels:batch?.pdf") == "labels_batch__edited.pdf"
    assert edited_pdf_filename(".pdf") == "shopee_labels_edited.pdf"
