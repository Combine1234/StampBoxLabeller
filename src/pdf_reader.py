from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterator, Sequence

try:
    import fitz
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by environment only
    raise ModuleNotFoundError(
        "PyMuPDF is required. Install dependencies with: pip install -r requirements.txt"
    ) from exc

from .models import LabelRecord
from .validator import normalize_key

LOGGER = logging.getLogger(__name__)

AUTO_GRID_VALUE = "auto"
AUTO_GRID_CANDIDATES: tuple[tuple[int, int], ...] = (
    (3, 3),
    (2, 2),
    (1, 2),
    (2, 1),
    (1, 1),
)

ORDER_PATTERN = re.compile(
    r"Shopee\s*Order\s*No\.?\s*[:#]?\s*([A-Z0-9]+)",
    re.IGNORECASE,
)
ORDER_FALLBACK_PATTERN = re.compile(
    r"Order\s*No\.?\s*[:#]?\s*([A-Z0-9]{8,})",
    re.IGNORECASE,
)
TRACKING_PATTERN = re.compile(r"\b\d{15,18}\b")


def open_pdf(file_path: str | Path) -> fitz.Document:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    return fitz.open(path)


def _grid_rects(page: fitz.Page, rows: int, columns: int) -> list[fitz.Rect]:
    if rows <= 0 or columns <= 0:
        raise ValueError("rows and columns must be positive")

    page_rect = page.rect
    cell_width = page_rect.width / columns
    cell_height = page_rect.height / rows
    labels: list[fitz.Rect] = []

    for row in range(rows):
        for col in range(columns):
            x0 = page_rect.x0 + col * cell_width
            y0 = page_rect.y0 + row * cell_height
            labels.append(fitz.Rect(x0, y0, x0 + cell_width, y0 + cell_height))
    return labels


def _count_order_numbers(text: str) -> int:
    matches = ORDER_PATTERN.findall(text) + ORDER_FALLBACK_PATTERN.findall(text)
    return len({normalize_key(match) for match in matches if normalize_key(match)})


def _words_in_rect(words: list[tuple], rect: fitz.Rect) -> list[tuple]:
    selected: list[tuple] = []
    for word in words:
        x0, y0, x1, y1, text, *_ = word
        if not str(text).strip():
            continue
        center = fitz.Point((float(x0) + float(x1)) / 2, (float(y0) + float(y1)) / 2)
        if center in rect:
            selected.append(word)
    return selected


def _text_from_words(words: list[tuple]) -> str:
    ordered = sorted(words, key=lambda word: (word[5] if len(word) > 5 else 0, word[6] if len(word) > 6 else 0, word[7] if len(word) > 7 else 0, word[1], word[0]))
    return " ".join(str(word[4]) for word in ordered if str(word[4]).strip())


def _text_bounds_from_words(words: list[tuple]) -> fitz.Rect | None:
    bounds: fitz.Rect | None = None
    for word in words:
        x0, y0, x1, y1, text, *_ = word
        if not str(text).strip():
            continue
        word_rect = fitz.Rect(x0, y0, x1, y1)
        bounds = word_rect if bounds is None else bounds | word_rect
    return bounds


def _text_bounds(page: fitz.Page, rect: fitz.Rect) -> fitz.Rect | None:
    return _text_bounds_from_words(page.get_text("words", clip=rect))


def _label_cell_score(words: list[tuple], rect: fitz.Rect, require_order: bool) -> tuple[float, bool]:
    rect_words = _words_in_rect(words, rect)
    text = _text_from_words(rect_words)
    order_count = _count_order_numbers(text)
    tracking_count = len(TRACKING_PATTERN.findall(text))
    if require_order and order_count == 0:
        return (0.0, False)
    if order_count == 0 and tracking_count == 0:
        return (0.0, False)

    bounds = _text_bounds_from_words(rect_words)
    width_ratio = (bounds.width / rect.width) if bounds and rect.width else 0.0
    height_ratio = (bounds.height / rect.height) if bounds and rect.height else 0.0
    duplicate_penalty = max(order_count - 1, 0) * 120.0
    score = 100.0 + min(width_ratio, 1.0) * 30.0 + min(height_ratio, 1.0) * 30.0
    score -= duplicate_penalty
    return (score, True)


def detect_label_rects(
    page: fitz.Page,
    candidates: Sequence[tuple[int, int]] = AUTO_GRID_CANDIDATES,
) -> list[fitz.Rect]:
    best_score = float("-inf")
    best_rects: list[fitz.Rect] = []
    page_words = page.get_text("words")
    page_text = _text_from_words(page_words)
    require_order = _count_order_numbers(page_text) > 0

    for rows, columns in candidates:
        detected: list[fitz.Rect] = []
        candidate_score = 0.0
        for rect in _grid_rects(page, rows, columns):
            score, has_label = _label_cell_score(page_words, rect, require_order=require_order)
            if has_label:
                detected.append(rect)
                candidate_score += score
            elif require_order and _text_bounds_from_words(_words_in_rect(page_words, rect)) is not None:
                candidate_score -= 180.0

        if not detected:
            continue

        candidate_score += len(detected) * 200.0
        if candidate_score > best_score:
            best_score = candidate_score
            best_rects = detected

    return best_rects or _grid_rects(page, 3, 3)


def _is_auto(value: int | str | None) -> bool:
    return value is None or str(value).strip().lower() == AUTO_GRID_VALUE


def split_page_into_labels(
    page: fitz.Page,
    rows: int | str | None = 3,
    columns: int | str | None = 3,
) -> list[fitz.Rect]:
    if _is_auto(rows) or _is_auto(columns):
        return detect_label_rects(page)
    return _grid_rects(page, int(rows), int(columns))


def extract_label_text(page: fitz.Page, label_rect: fitz.Rect) -> str:
    return page.get_text("text", clip=label_rect) or ""


def extract_order_no(text: str) -> str | None:
    matches = [normalize_key(match) for match in ORDER_PATTERN.findall(text)]
    if not matches:
        matches = [normalize_key(match) for match in ORDER_FALLBACK_PATTERN.findall(text)]
    matches = [match for match in matches if match]
    return matches[0] if matches else None


def extract_tracking_no_from_text(text: str) -> str | None:
    match = TRACKING_PATTERN.search(text)
    return match.group(0) if match else None


def _candidate_tracking_words(
    page: fitz.Page,
    clip: fitz.Rect,
) -> list[tuple[float, float, str]]:
    candidates: list[tuple[float, float, str]] = []
    for word in page.get_text("words", clip=clip):
        x0, y0, _x1, _y1, text, *_ = word
        normalized = str(text).strip()
        if TRACKING_PATTERN.fullmatch(normalized):
            candidates.append((float(y0), float(x0), normalized))
    return candidates


def extract_tracking_no(page: fitz.Page, label_rect: fitz.Rect) -> str | None:
    width = label_rect.width
    height = label_rect.height
    top_clip = fitz.Rect(
        label_rect.x0,
        label_rect.y0,
        label_rect.x0 + width,
        label_rect.y0 + height * 0.35,
    )

    candidates = _candidate_tracking_words(page, top_clip)
    if not candidates:
        candidates = _candidate_tracking_words(page, label_rect)
    if not candidates:
        return None

    candidates.sort()
    return candidates[0][2]


def iter_label_records(
    pdf_path: str | Path,
    rows: int = 3,
    columns: int = 3,
) -> Iterator[LabelRecord]:
    with open_pdf(pdf_path) as doc:
        global_index = 0
        for page_index, page in enumerate(doc, start=1):
            for label_index, label_rect in enumerate(
                split_page_into_labels(page, rows=rows, columns=columns),
                start=1,
            ):
                global_index += 1
                text = extract_label_text(page, label_rect)
                order_no = extract_order_no(text)
                tracking_no = extract_tracking_no(page, label_rect)
                yield LabelRecord(
                    page=page_index,
                    label_index=label_index,
                    global_index=global_index,
                    order_no=order_no,
                    tracking_no=tracking_no,
                    text=text,
                    rect=label_rect,
                )
