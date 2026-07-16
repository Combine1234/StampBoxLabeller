from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MatchResult:
    status: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass(slots=True)
class DataIndex:
    by_tracking: dict[str, list[dict[str, Any]]]
    by_order: dict[str, list[dict[str, Any]]]
    rows: list[dict[str, Any]]


@dataclass(slots=True)
class LabelRecord:
    page: int
    label_index: int
    global_index: int
    order_no: str | None
    tracking_no: str | None
    text: str
    rect: Any

