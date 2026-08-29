from __future__ import annotations

import fitz

from src.stamp_guard import (
    is_stampbox_output_pdf,
    looks_like_stampbox_output_name,
    mark_stampbox_output,
)


def test_detects_processed_output_filename() -> None:
    assert looks_like_stampbox_output_name("labels_พร้อมส่งลูกค้า_20260717.pdf")
    assert looks_like_stampbox_output_name("labels_พร_อมส_งล_กค_า_20260717.pdf")
    assert looks_like_stampbox_output_name("SG Flash - 133 17.7_edited.pdf")
    assert not looks_like_stampbox_output_name("SG Flash - 133 17.7.pdf")


def test_detects_stampbox_metadata_after_file_is_renamed(tmp_path) -> None:
    output_pdf = tmp_path / "renamed.pdf"
    doc = fitz.open()
    doc.new_page()
    mark_stampbox_output(doc)
    doc.save(output_pdf)
    doc.close()

    assert is_stampbox_output_pdf(output_pdf)
