from __future__ import annotations

from pathlib import Path


def safe_output_stem(filename: str) -> str:
    name = Path(filename).name.strip()
    stem = name[:-4] if name.casefold().endswith(".pdf") else Path(name).stem
    stem = stem.strip(" .") or "shopee_labels"
    cleaned = "".join(
        char if char.isalnum() or char in (" ", "-", "_", ".") else "_"
        for char in stem
    ).strip(" .")
    return cleaned or "shopee_labels"


def edited_pdf_filename(filename: str) -> str:
    return f"{safe_output_stem(filename)}_edited.pdf"
