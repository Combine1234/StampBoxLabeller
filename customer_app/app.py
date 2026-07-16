from __future__ import annotations

import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.overlay_writer import create_output_pdf, locate_font
from src.pdf_product_extractor import build_rows_from_pdf
from src.preview import render_page
from src.product_mapping import DEFAULT_MAPPING_URL
from src.report import report_to_excel_bytes

logging.basicConfig(level=logging.INFO)

OUTPUT_DIR = PROJECT_ROOT / "output" / "customer"
LOCKED_MAPPING_URL = DEFAULT_MAPPING_URL


st.set_page_config(
    page_title="Shopee PDF Label",
    page_icon="PDF",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 860px;
        padding-top: 2rem;
    }
    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: .25rem;
    }
    .subtitle {
        color: #475569;
        font-size: 1rem;
        margin-bottom: 1.25rem;
    }
    div[data-testid="stFileUploader"] section {
        border: 2px dashed #2563EB;
        background: #F8FAFC;
        border-radius: 8px;
        padding: 1.25rem;
    }
    div[data-testid="stDownloadButton"] button {
        background: #0057D9;
        color: white;
        border-radius: 8px;
        font-weight: 700;
        min-height: 3rem;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: #0048B5;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _safe_output_name(upload_name: str) -> str:
    stem = Path(upload_name).stem.strip() or "shopee_labels"
    cleaned = "".join(char if char.isalnum() or char in (" ", "-", "_") else "_" for char in stem).strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{cleaned}_พร้อมส่งลูกค้า_{timestamp}.pdf"


def _status_counts(report_rows: list[dict]) -> tuple[int, int, int]:
    written = sum(1 for row in report_rows if row.get("status") == "WRITTEN")
    failed = sum(1 for row in report_rows if row.get("status") not in {"WRITTEN", "MATCHED"})
    total = len([row for row in report_rows if int(row.get("page") or 0) > 0])
    return written, failed, total


def _process_pdf(uploaded_file) -> dict:
    progress = st.progress(0, text="0% กำลังรับไฟล์ PDF")
    status = st.empty()

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        input_pdf = temp_dir / "labels.pdf"
        input_pdf.write_bytes(uploaded_file.getvalue())
        progress.progress(10, text="10% รับไฟล์เรียบร้อย")

        status.info("กำลังอ่านรายการสินค้าในใบปะหน้า")
        rows = build_rows_from_pdf(input_pdf, mapping_source=LOCKED_MAPPING_URL)
        progress.progress(40, text="40% อ่านสินค้าและจับคู่กับ Google Sheet แล้ว")

        resolved_font = locate_font()
        if not resolved_font:
            raise RuntimeError("ไม่พบฟอนต์ภาษาไทยในเครื่อง")

        output_pdf = temp_dir / "labels_ready.pdf"
        status.info("กำลังเขียนโค้ดสินค้าและจำนวนลง PDF")
        report_rows = create_output_pdf(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            excel_rows=rows,
            font_path=resolved_font,
        )
        progress.progress(85, text="85% เขียน PDF เสร็จแล้ว กำลังเตรียมไฟล์")

        pdf_bytes = output_pdf.read_bytes()
        report_bytes = report_to_excel_bytes(report_rows)
        preview_png = render_page(output_pdf, page_index=0)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        saved_pdf = OUTPUT_DIR / _safe_output_name(uploaded_file.name)
        saved_pdf.write_bytes(pdf_bytes)

        progress.progress(100, text="100% เสร็จแล้ว")
        status.success("พร้อมบันทึกไฟล์ให้ลูกค้า")

    return {
        "pdf_bytes": pdf_bytes,
        "report_bytes": report_bytes,
        "preview_png": preview_png,
        "report_rows": report_rows,
        "source_rows": rows,
        "saved_pdf": saved_pdf,
        "download_name": saved_pdf.name,
    }


st.markdown('<div class="main-title">ทำใบปะหน้า Shopee</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">อัปโหลด PDF แล้วระบบจะอ่านสินค้า จับคู่โค้ดจาก Sheet และเขียนลงใบปะหน้าให้อัตโนมัติ</div>',
    unsafe_allow_html=True,
)

uploaded_pdf = st.file_uploader(
    "อัปโหลด PDF",
    type=["pdf"],
    accept_multiple_files=False,
    help="ลากไฟล์ PDF มาวางตรงนี้ หรือคลิกเพื่อเลือกไฟล์",
    label_visibility="collapsed",
)

if not uploaded_pdf:
    st.info("ลากไฟล์ PDF มาวาง หรือคลิกกล่องด้านบนเพื่อเลือกไฟล์")
    st.stop()

file_key = f"{uploaded_pdf.name}:{uploaded_pdf.size}"
if st.session_state.get("processed_file_key") != file_key:
    try:
        st.session_state["customer_result"] = _process_pdf(uploaded_pdf)
        st.session_state["processed_file_key"] = file_key
    except Exception as exc:  # pragma: no cover - Streamlit surface
        st.error(f"ทำไฟล์ไม่สำเร็จ: {exc}")
        st.stop()

result = st.session_state["customer_result"]
written, failed, total = _status_counts(result["report_rows"])

col_a, col_b, col_c = st.columns(3)
col_a.metric("ใบปะหน้าที่เขียนสำเร็จ", written)
col_b.metric("ใบปะหน้าทั้งหมด", total)
col_c.metric("รายการที่ต้องเช็ก", failed)

st.download_button(
    "บันทึก PDF พร้อมส่งลูกค้า",
    data=result["pdf_bytes"],
    file_name=result["download_name"],
    mime="application/pdf",
    use_container_width=True,
    type="primary",
)

with st.expander("ดูตัวอย่างหน้าแรก", expanded=True):
    st.image(result["preview_png"], use_container_width=True)

with st.expander("ดูรายละเอียดการทำงาน"):
    st.caption(f"บันทึกสำเนาไว้ที่: {result['saved_pdf']}")
    st.dataframe(pd.DataFrame(result["report_rows"]), use_container_width=True, hide_index=True)
    st.download_button(
        "ดาวน์โหลดรายงาน Excel",
        data=result["report_bytes"],
        file_name=Path(result["download_name"]).with_suffix(".xlsx").name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
