from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from google_ads_audit.ai import generate_ai_summary
from google_ads_audit.analysis import run_audit
from google_ads_audit.cleaning import read_google_ads_csv
from google_ads_audit.config import load_config
from google_ads_audit.reporting import export_excel, export_json, export_pdf


st.set_page_config(page_title="Google Ads Audit System", page_icon="GA", layout="wide")

st.title("Google Ads Audit System")
st.caption("CSV-based audit engine for campaign, keyword, search term, conversion, location, device, auction, and change-history analysis.")

with st.sidebar:
    st.header("Audit Settings")
    use_ai = st.toggle("Generate AI consultant summary", value=False)
    st.caption("AI receives computed metrics JSON only, never raw CSV rows.")

uploaded_files = st.file_uploader(
    "Upload Google Ads CSV exports",
    type=["csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    config = load_config()
    imported = []
    for uploaded in uploaded_files:
        report = read_google_ads_csv(uploaded, source_name=uploaded.name)
        imported.append(report)

    result = run_audit(imported, config)
    if use_ai:
        with st.spinner("Generating consultant summary from computed metrics..."):
            result.ai_summary = generate_ai_summary(result.metrics)

    score_cols = st.columns(5)
    score_cols[0].metric("Overall Score", f"{result.scores.overall}/100")
    score_cols[1].metric("Findings", len(result.findings))
    score_cols[2].metric("High Priority", sum(1 for f in result.findings if f.priority.value == "High"))
    score_cols[3].metric("Reports Loaded", len(result.reports))
    score_cols[4].metric("Charts", len(result.charts))

    st.subheader("Account Health Score")
    st.dataframe(pd.DataFrame([result.scores.as_dict()]), use_container_width=True)

    if result.ai_summary:
        st.subheader("AI Consultant Summary")
        st.write(result.ai_summary)

    st.subheader("Priority Findings")
    findings_df = pd.DataFrame(
        [
            {
                "Priority": item.priority.value,
                "Category": item.category,
                "Issue": item.title,
                "Evidence": item.evidence,
                "Recommendation": item.recommendation,
            }
            for item in result.findings
        ]
    )
    st.dataframe(findings_df, use_container_width=True, hide_index=True)

    st.subheader("Charts")
    for name, figure in result.charts.items():
        st.plotly_chart(figure, use_container_width=True)

    st.subheader("Imported Reports")
    for report_type, frame in result.reports.items():
        with st.expander(f"{report_type.value} ({len(frame):,} rows)"):
            st.dataframe(frame.head(1000), use_container_width=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_path = export_json(result, tmp_path / "audit_metrics.json")
        excel_path = export_excel(result, tmp_path / "google_ads_audit.xlsx")
        pdf_path = export_pdf(result, tmp_path / "google_ads_audit.pdf")

        st.subheader("Downloads")
        col1, col2, col3 = st.columns(3)
        col1.download_button(
            "Download JSON",
            data=json_path.read_bytes(),
            file_name="audit_metrics.json",
            mime="application/json",
        )
        col2.download_button(
            "Download Excel",
            data=excel_path.read_bytes(),
            file_name="google_ads_audit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        col3.download_button(
            "Download PDF",
            data=pdf_path.read_bytes(),
            file_name="google_ads_audit.pdf",
            mime="application/pdf",
        )
else:
    st.info("Upload one or more CSV exports from Google Ads to begin the audit.")
