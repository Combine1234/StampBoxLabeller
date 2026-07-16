from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.excel_reader import rows_from_dataframe
from src.overlay_writer import analyze_pdf, create_output_pdf, locate_font
from src.pdf_product_extractor import build_rows_from_pdf
from src.product_mapping import DEFAULT_MAPPING_URL
from src.preview import render_page, render_page_with_report
from src.report import report_to_excel_bytes

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Shopee Label Overlay", layout="wide")
st.title("Shopee Label Code Overlay")


def _write_uploaded(uploaded_file, path: Path) -> Path:
    path.write_bytes(uploaded_file.getvalue())
    return path


def _prepare_rows(
    pdf_path: Path,
    edited_df: pd.DataFrame | None,
    mapping_source: str,
) -> list[dict]:
    if edited_df is not None:
        return rows_from_dataframe(edited_df)
    return build_rows_from_pdf(pdf_path, mapping_source=mapping_source)


with st.sidebar:
    st.header("Files")
    pdf_file = st.file_uploader("Upload Shopee label PDF", type=["pdf"])
    excel_file = st.file_uploader("Upload Excel override (optional)", type=["xlsx"])
    mapping_url = st.text_input("Google Sheet mapping URL", value=DEFAULT_MAPPING_URL)
    custom_font = st.text_input("Font path (optional)", value="")
    resolved_font = locate_font(custom_font or None)
    if resolved_font:
        st.caption(f"Font: {resolved_font}")
    else:
        st.warning("No Thai-capable font found")

edited_df: pd.DataFrame | None = None
if excel_file:
    source_df = pd.read_excel(excel_file, dtype=object)
    edited_df = st.data_editor(
        source_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
    )
else:
    st.info("Upload only a PDF to auto-read product rows. Upload Excel later when you want to override product_code.")

if pdf_file:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        check_clicked = st.button("Check / Preview", use_container_width=True)
    with col_b:
        create_clicked = st.button("Create PDF + Report", use_container_width=True, type="primary")

    if check_clicked:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                temp_dir = Path(tmp)
                pdf_path = _write_uploaded(pdf_file, temp_dir / "labels.pdf")
                rows = _prepare_rows(pdf_path, edited_df, mapping_url)
                st.session_state["source_rows"] = rows
                report_rows = analyze_pdf(pdf_path, rows)
                st.session_state["report_rows"] = report_rows
                st.session_state["preview_png"] = render_page_with_report(pdf_path, report_rows, page_index=0)
                st.session_state.pop("output_pdf", None)
                st.session_state.pop("report_xlsx", None)
        except Exception as exc:  # pragma: no cover - Streamlit surface
            st.error(str(exc))

    if create_clicked:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                temp_dir = Path(tmp)
                pdf_path = _write_uploaded(pdf_file, temp_dir / "labels.pdf")
                rows = _prepare_rows(pdf_path, edited_df, mapping_url)
                output_pdf = temp_dir / "labels_overlay.pdf"
                report_rows = create_output_pdf(
                    input_pdf=pdf_path,
                    output_pdf=output_pdf,
                    excel_rows=rows,
                    font_path=resolved_font,
                )
                st.session_state["source_rows"] = rows
                st.session_state["report_rows"] = report_rows
                st.session_state["output_pdf"] = output_pdf.read_bytes()
                st.session_state["report_xlsx"] = report_to_excel_bytes(report_rows)
                st.session_state["preview_png"] = render_page(output_pdf, page_index=0)
        except Exception as exc:  # pragma: no cover - Streamlit surface
            st.error(str(exc))

if st.session_state.get("source_rows"):
    st.subheader("Rows To Write")
    st.dataframe(pd.DataFrame(st.session_state["source_rows"]), use_container_width=True, hide_index=True)

if st.session_state.get("report_rows"):
    st.subheader("Match Report")
    st.dataframe(pd.DataFrame(st.session_state["report_rows"]), use_container_width=True, hide_index=True)

if st.session_state.get("preview_png"):
    st.subheader("First Page Preview")
    st.image(st.session_state["preview_png"], use_container_width=True)

if st.session_state.get("output_pdf") and st.session_state.get("report_xlsx"):
    col_pdf, col_report = st.columns([1, 1])
    with col_pdf:
        st.download_button(
            "Download PDF",
            data=st.session_state["output_pdf"],
            file_name="labels_overlay.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_report:
        st.download_button(
            "Download report",
            data=st.session_state["report_xlsx"],
            file_name="report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
