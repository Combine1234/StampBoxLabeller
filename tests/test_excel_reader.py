from __future__ import annotations

import pandas as pd
import pytest

from src.excel_reader import rows_from_dataframe


def test_rows_from_dataframe_normalizes_and_filters_enabled() -> None:
    df = pd.DataFrame(
        [
            {
                "order_no": " 2607060SXN316F ",
                "tracking_no": 5910552865138006,
                "variant": "เมเปิ้ล",
                "quantity": 1.0,
                "enabled": True,
            },
            {
                "order_no": "SKIP",
                "variant": "ไม่ใช้",
                "quantity": 1,
                "enabled": "no",
            },
        ]
    )

    rows = rows_from_dataframe(df)

    assert len(rows) == 1
    assert rows[0]["order_no"] == "2607060SXN316F"
    assert rows[0]["tracking_no"] == "5910552865138006"
    assert rows[0]["quantity"] == "1"


def test_rows_from_dataframe_requires_columns() -> None:
    df = pd.DataFrame([{"order_no": "A", "quantity": 1}])

    with pytest.raises(ValueError):
        rows_from_dataframe(df)
