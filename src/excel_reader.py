from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .validator import normalize_row, validate_excel_columns as validate_columns


def validate_excel_columns(rows_or_columns: Iterable[Any]) -> list[str]:
    materialized = list(rows_or_columns)
    if not materialized:
        return validate_columns([])
    first = materialized[0]
    if isinstance(first, dict):
        return validate_columns(first.keys())
    return validate_columns(str(column) for column in materialized)


def rows_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    errors = validate_columns(df.columns)
    if errors:
        raise ValueError("; ".join(errors))

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(df.to_dict("records"), start=2):
        row = normalize_row(raw, source_row=index)
        if row["enabled"]:
            rows.append(row)
    return rows


def read_excel(file_path: str | Path) -> list[dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    df = pd.read_excel(path, dtype=object)
    return rows_from_dataframe(df)

