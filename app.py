"""
Financial Data Normalizer — Before/After View

Shows raw input on the left, normalized output on the right.
Run with: streamlit run app.py
"""

import json
import os
import tempfile
from datetime import date

import pandas as pd
import streamlit as st

from core.ingest import ingest_file
from core.result import NormalizedResult


st.set_page_config(page_title="Financial Data Normalizer", page_icon="📊", layout="wide")

# ── Sidebar: pick a file ──
with st.sidebar:
    st.markdown("## 📊 Data Normalizer")
    st.divider()

    doc_category = st.selectbox("Document Type", [
        "Income Statement / P&L",
        "Balance Sheet",
        "Cash Flow",
        "Trial Balance",
        "Working Capital / AR-AP",
        "Revenue Detail",
        "Cost Detail",
        "KPI / Operational",
        "Upload my own file",
    ])

    DEMO_MAP = {
        "Income Statement / P&L": [
            ("Clean CSV", "data/sample_pl.csv", "Meridian Software", "B2B SaaS"),
            ("QuickBooks Export (messy CSV)", "data/test/quickbooks_export.csv", "Acme Corp", "B2B SaaS"),
            ("Manufacturing (multi-sheet Excel)", "data/test/manufacturing_pl.xlsx", "Atlas Manufacturing", "Manufacturing"),
            ("Services (combined SG&A)", "data/test/services_company.xlsx", "Summit Consulting", "Services"),
            ("Messy $000s Workbook", "data/test/messy_workbook.xlsx", "Meridian Software", "B2B SaaS"),
            ("PDF Board Pack", "data/test/pl_board_pack.pdf", "Meridian Software", "B2B SaaS"),
        ],
        "Balance Sheet": [
            ("Clean CSV", "data/test/balance_sheet_clean.csv", "Meridian Software", "B2B SaaS"),
            ("PDF Report", "data/test/balance_sheet_report.pdf", "Meridian Software", "B2B SaaS"),
        ],
        "Cash Flow": [("Clean CSV", "data/test/cash_flow_clean.csv", "Meridian Software", "B2B SaaS")],
        "Trial Balance": [("Clean CSV", "data/test/trial_balance_clean.csv", "Meridian Software", "B2B SaaS")],
        "Working Capital / AR-AP": [("Clean CSV", "data/test/working_capital_clean.csv", "Meridian Software", "B2B SaaS")],
        "Revenue Detail": [("Clean CSV", "data/test/revenue_detail_clean.csv", "Meridian Software", "B2B SaaS")],
        "Cost Detail": [("Clean CSV", "data/test/cost_detail_clean.csv", "Meridian Software", "B2B SaaS")],
        "KPI / Operational": [("Clean CSV", "data/test/kpi_operational_clean.csv", "Meridian Software", "B2B SaaS")],
    }

    filepath = None
    company_name = ""
    business_type = ""
    uploaded_file = None

    if doc_category == "Upload my own file":
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx", "xls", "pdf"])
        company_name = st.text_input("Company Name", "")
        business_type = st.selectbox("Business Type", ["B2B SaaS", "Services", "Manufacturing", "Distribution", "Other"])
    else:
        demos = DEMO_MAP[doc_category]
        if len(demos) == 1:
            _, filepath, company_name, business_type = demos[0]
        else:
            choice = st.radio("Demo file", [d[0] for d in demos])
            for d in demos:
                if d[0] == choice:
                    _, filepath, company_name, business_type = d
                    break

    st.divider()
    run = st.button("🚀 Normalize", type="primary", use_container_width=True)
    st.divider()
    st.caption("Supports: CSV · Excel · PDF")
    st.caption("8 document types auto-detected")


# ── Main area ──
st.markdown("## Financial Data Normalizer")
st.caption("Before → After: See how messy financial data gets cleaned and structured")

# Resolve filepath
actual_filepath = filepath
if doc_category == "Upload my own file":
    if uploaded_file is None:
        st.info("Upload a file in the sidebar and click Normalize.")
        st.stop()
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        actual_filepath = tmp.name

if not run:
    # Show just the raw input preview before they click
    st.markdown(f"**Selected:** `{os.path.basename(actual_filepath)}`")
    ext = os.path.splitext(actual_filepath)[1].lower()
    try:
        if ext == ".csv":
            with open(actual_filepath, "r", errors="replace") as f:
                raw_lines = f.read().strip().split("\n")[:20]
            st.code("\n".join(raw_lines), language=None)
        elif ext in (".xlsx", ".xls"):
            st.dataframe(pd.read_excel(actual_filepath, header=None, nrows=15), use_container_width=True, hide_index=False)
        elif ext == ".pdf":
            st.info("PDF file — will extract tables on normalize")
    except Exception as e:
        st.warning(f"Preview: {e}")
    st.caption("Click **Normalize** in the sidebar to process this file")
    st.stop()


# ── Run the pipeline ──
with st.spinner("Normalizing..."):
    try:
        result: NormalizedResult = ingest_file(
            actual_filepath, company_name=company_name, business_type=business_type,
        )
    except Exception as e:
        st.error(f"Failed: {e}")
        st.stop()

# ── Before / After side by side ──

left, right = st.columns(2)

# ── LEFT: Before (raw input) ──
with left:
    st.markdown("### 📄 BEFORE (Raw Input)")
    st.caption(f"`{os.path.basename(actual_filepath)}`")

    ext = os.path.splitext(actual_filepath)[1].lower()
    try:
        if ext == ".csv":
            with open(actual_filepath, "r", errors="replace") as f:
                raw_lines = f.read().strip().split("\n")
            st.code("\n".join(raw_lines[:20]), language=None)
            if len(raw_lines) > 20:
                st.caption(f"...{len(raw_lines) - 20} more lines")
        elif ext in (".xlsx", ".xls"):
            raw_df = pd.read_excel(actual_filepath, header=None, nrows=20)
            st.dataframe(raw_df, use_container_width=True, hide_index=False, height=400)
        elif ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(actual_filepath) as pdf:
                tables = []
                for page in pdf.pages:
                    tables.extend(page.extract_tables())
                if tables:
                    all_rows = []
                    for t in tables:
                        all_rows.extend(t)
                    raw_df = pd.DataFrame(all_rows)
                    st.dataframe(raw_df, use_container_width=True, hide_index=False, height=400)
                else:
                    st.info("No tables extracted from PDF")
    except Exception as e:
        st.warning(f"Could not preview: {e}")

# ── RIGHT: After (normalized) ──
with right:
    st.markdown("### ✅ AFTER (Normalized)")

    # Method badge
    if result.used_fallback:
        method = "🆘 Code-gen fallback"
    elif result.used_ai:
        method = "🤖 AI normalized"
    else:
        method = "⚡ Fast path (no AI)"

    st.caption(f"Detected: **{result.doc_type_name}** · {method} · Quality: **{result.quality_score:.0f}/100**")

    # Formatted output table
    display_df = result.df.copy()
    for col in display_df.columns:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and abs(x) >= 100 else (f"{x:.2f}" if pd.notna(x) and isinstance(x, float) else (str(x) if pd.notna(x) else ""))
            )
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

st.divider()

# ── Bottom section: details ──
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Quality", f"{result.quality_score:.0f}/100")
with c2:
    st.metric("Rows", len(result.df))
with c3:
    st.metric("Columns", len(result.df.columns))
with c4:
    st.metric("Doc Type", result.doc_type.replace("_", " ").title()[:15])
with c5:
    st.metric("AI Used", "Yes" if result.used_ai else "No")

# Audit trail + warnings
col_a, col_b = st.columns(2)
with col_a:
    if result.audit_trail:
        with st.expander(f"📝 Audit Trail ({len(result.audit_trail)} steps)", expanded=False):
            icons = {
                "renamed": "📛", "auto_fill_zero": "⚠️", "derived": "🔢",
                "auto_corrected": "🔧", "row_dropped": "🗑️", "multiplier_applied": "✖️",
                "mapped_sum": "➕", "fallback_used": "🆘", "auto_sorted": "📅",
            }
            for entry in result.audit_trail:
                icon = icons.get(entry["action"], "•")
                st.write(f"{icon} {entry['detail']}")
    if result.warnings:
        with st.expander(f"⚠️ Warnings ({len(result.warnings)})"):
            for w in result.warnings:
                st.warning(w)

with col_b:
    if result.quality_report:
        qr = result.quality_report
        with st.expander("📊 Quality Breakdown", expanded=False):
            st.write(f"**Completeness:** {qr.completeness_score:.0f}/100 — non-null required cells")
            st.write(f"**Consistency:** {qr.consistency_score:.0f}/100 — accounting identities hold")
            st.write(f"**Coverage:** {qr.coverage_score:.0f}/100 — temporal completeness")
            st.write(f"**Reasonableness:** {qr.reasonableness_score:.0f}/100 — values in expected range")

# Export
st.divider()
col_e1, col_e2 = st.columns(2)
with col_e1:
    st.download_button("📥 Download Normalized CSV", result.df.to_csv(index=False),
                       file_name=f"normalized_{date.today().isoformat()}.csv",
                       mime="text/csv", use_container_width=True)
with col_e2:
    output = {
        "source": os.path.basename(actual_filepath),
        "doc_type": result.doc_type,
        "quality_score": result.quality_score,
        "used_ai": result.used_ai,
        "audit_trail": result.audit_trail,
        "data": result.df.to_dict(orient="records"),
    }
    st.download_button("📥 Download JSON", json.dumps(output, indent=2, default=str),
                       file_name=f"normalized_{date.today().isoformat()}.json",
                       mime="application/json", use_container_width=True)
