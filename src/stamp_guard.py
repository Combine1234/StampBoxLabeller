from __future__ import annotations

import unicodedata
from pathlib import Path

import fitz


STAMPBOX_METADATA_MARKER = "stampbox-processed"
OUTPUT_NAME_MARKER = "พร้อมส่งลูกค้า"
OUTPUT_NAME_SUFFIX = "_edited"


def _compact_marker(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def looks_like_stampbox_output_name(filename: str) -> bool:
    stem = Path(filename).stem
    compact_name = _compact_marker(stem)
    return (
        _compact_marker(OUTPUT_NAME_MARKER) in compact_name
        or stem.casefold().strip().endswith(OUTPUT_NAME_SUFFIX)
    )


def mark_stampbox_output(doc: fitz.Document) -> None:
    metadata = dict(doc.metadata or {})
    keywords = str(metadata.get("keywords") or "").strip()
    existing = {item.strip().casefold() for item in keywords.split(",") if item.strip()}
    if STAMPBOX_METADATA_MARKER not in existing:
        keywords = ", ".join(item for item in (keywords, STAMPBOX_METADATA_MARKER) if item)
    metadata["keywords"] = keywords
    metadata["producer"] = "StampBOX"
    doc.set_metadata(metadata)


def is_stampbox_output_pdf(path: str | Path, filename: str = "") -> bool:
    if filename and looks_like_stampbox_output_name(filename):
        return True

    with fitz.open(path) as doc:
        metadata = doc.metadata or {}
        searchable = " ".join(
            str(metadata.get(key) or "")
            for key in ("producer", "creator", "subject", "keywords")
        ).casefold()
    return STAMPBOX_METADATA_MARKER in searchable
