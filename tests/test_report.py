from __future__ import annotations

from openpyxl import load_workbook

from src.report import save_report_excel


def test_save_report_excel(tmp_path) -> None:
    report_path = tmp_path / "report.xlsx"
    save_report_excel(
        [
            {
                "page": 1,
                "label_index": 1,
                "global_index": 1,
                "order_no": "ORDER1",
                "tracking_no": "1234567890123456",
                "status": "WRITTEN",
                "message": "Success",
            }
        ],
        report_path,
    )

    workbook = load_workbook(report_path)
    sheet = workbook["Report"]
    assert sheet["A1"].value == "page"
    assert sheet["F2"].value == "WRITTEN"

