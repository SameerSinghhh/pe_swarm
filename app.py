"""
PE Value Creation Platform — Data Ingestion + Analysis

Full pipeline: Upload → Normalize → Analyze → Results
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
from analysis.engine import run_analysis
from analysis.types import Favorability, Severity


st.set_page_config(page_title="PE Value Creation Platform", page_icon="📊", layout="wide")

# ── Custom CSS ──
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #6366f1;
    }
    .flag-critical { border-left: 4px solid #ef4444; background: #fef2f2; padding: 8px 12px; border-radius: 6px; margin: 4px 0; }
    .flag-warning { border-left: 4px solid #f59e0b; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin: 4px 0; }
    .flag-info { border-left: 4px solid #3b82f6; background: #eff6ff; padding: 8px 12px; border-radius: 6px; margin: 4px 0; }
    .bridge-positive { color: #10b981; font-weight: 600; }
    .bridge-negative { color: #ef4444; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## 📊 PE Value Creation")
    st.caption("Upload → Normalize → Analyze")
    st.divider()

    mode = st.radio("Mode", ["Demo Data (all types)", "Upload my own file"])

    DEMO_FILES = {
        "P&L — Clean CSV": ("data/sample_pl.csv", "Meridian Software", "B2B SaaS"),
        "P&L — QuickBooks Export": ("data/test/quickbooks_export.csv", "Acme Corp", "B2B SaaS"),
        "P&L — Manufacturing Excel": ("data/test/manufacturing_pl.xlsx", "Atlas Manufacturing", "Manufacturing"),
        "P&L — Messy $000s Workbook": ("data/test/messy_workbook.xlsx", "Meridian Software", "B2B SaaS"),
        "P&L — PDF Board Pack": ("data/test/pl_board_pack.pdf", "Meridian Software", "B2B SaaS"),
        "Balance Sheet": ("data/test/balance_sheet_clean.csv", "Meridian Software", "B2B SaaS"),
        "Cash Flow Statement": ("data/test/cash_flow_clean.csv", "Meridian Software", "B2B SaaS"),
        "Working Capital / AR Aging": ("data/test/working_capital_clean.csv", "Meridian Software", "B2B SaaS"),
        "Revenue Detail (by product)": ("data/test/revenue_detail_clean.csv", "Meridian Software", "B2B SaaS"),
        "Cost Detail (by dept)": ("data/test/cost_detail_clean.csv", "Meridian Software", "B2B SaaS"),
        "KPI / Operational Metrics": ("data/test/kpi_operational_clean.csv", "Meridian Software", "B2B SaaS"),
    }

    uploaded_file = None
    selected_files = {}

    if mode == "Upload my own file":
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx", "xls", "pdf"])
        company_name = st.text_input("Company Name", "")
        business_type = st.selectbox("Business Type", ["B2B SaaS", "Services", "Manufacturing", "Distribution", "Other"])
    else:
        st.caption("Select files to analyze together:")
        for label, (path, company, btype) in DEMO_FILES.items():
            if st.checkbox(label, value=(label == "P&L — Clean CSV")):
                selected_files[label] = (path, company, btype)

    st.divider()
    run = st.button("🚀 Run Full Analysis", type="primary", use_container_width=True)


# ── Main ──
st.markdown("# PE Value Creation Platform")
st.caption("Data Ingestion → Normalization → Financial Analysis → Trend Detection")

if not run:
    st.info("Select data in the sidebar and click **Run Full Analysis**.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: INGEST
# ═══════════════════════════════════════════════════════════════════════════

st.header("① Data Ingestion")

ingested: dict[str, NormalizedResult] = {}

if mode == "Upload my own file":
    if uploaded_file is None:
        st.warning("Upload a file first.")
        st.stop()
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        filepath = tmp.name
    with st.spinner(f"Ingesting {uploaded_file.name}..."):
        try:
            result = ingest_file(filepath, company_name=company_name, business_type=business_type)
            ingested[result.doc_type] = result
        except Exception as e:
            st.error(f"Failed: {e}")
            st.stop()
else:
    if not selected_files:
        st.warning("Select at least one file.")
        st.stop()

    progress = st.progress(0)
    status_text = st.empty()
    for i, (label, (path, company, btype)) in enumerate(selected_files.items()):
        status_text.text(f"Ingesting: {label}...")
        try:
            result = ingest_file(path, company_name=company, business_type=btype)
            ingested[result.doc_type] = result
        except Exception as e:
            st.warning(f"Failed to ingest {label}: {e}")
        progress.progress((i + 1) / len(selected_files))
    status_text.empty()
    progress.empty()

# Show ingestion summary
cols = st.columns(len(ingested))
for i, (doc_type, result) in enumerate(ingested.items()):
    with cols[i]:
        method = "⚡ Fast" if not result.used_ai else ("🆘 Fallback" if result.used_fallback else "🤖 AI")
        st.metric(result.doc_type_name.split("/")[0].strip()[:20], f"{len(result.df)} rows", method)

if not ingested:
    st.error("No data ingested.")
    st.stop()

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

st.header("② Analysis Engine")

with st.spinner("Running all analysis modules..."):
    analysis = run_analysis(ingested)

st.success(f"**{len(analysis.modules_run)} modules completed:** {', '.join(analysis.modules_run)}")

if analysis.warnings:
    for w in analysis.warnings:
        st.warning(w)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: RESULTS
# ═══════════════════════════════════════════════════════════════════════════

st.header("③ Results")

# ── Tab layout ──
tab_names = []
if analysis.ebitda_bridges: tab_names.append("EBITDA Bridge")
if analysis.margins: tab_names.append("Margins & Growth")
if analysis.variance: tab_names.append("Variance Analysis")
if analysis.working_capital: tab_names.append("Working Capital")
if analysis.fcf: tab_names.append("FCF & Leverage")
if analysis.revenue_analytics: tab_names.append("Revenue Analytics")
if analysis.trends: tab_names.append("Trend Flags")

if not tab_names:
    st.info("No analysis results to display.")
    st.stop()

tabs = st.tabs(tab_names)
tab_idx = 0


# ── EBITDA Bridge Tab ──
if analysis.ebitda_bridges:
    with tabs[tab_idx]:
        eb = analysis.ebitda_bridges

        bridge_cols = st.columns(3 if eb.vs_prior_year else (2 if eb.vs_budget else 1))

        def render_bridge(bridge, col):
            if bridge is None:
                return
            with col:
                st.subheader(bridge.label)
                st.caption(f"{bridge.base_period} → {bridge.current_period}")

                # Base
                st.markdown(f"**Starting EBITDA:** ${bridge.base_ebitda:,.0f}")

                # Components
                for comp in bridge.components:
                    color = "bridge-positive" if comp.value >= 0 else "bridge-negative"
                    st.markdown(
                        f'<div style="display:flex; justify-content:space-between; padding:4px 0;">'
                        f'<span>{comp.name}</span>'
                        f'<span class="{color}">${comp.value:+,.0f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("---")
                st.markdown(f"**Ending EBITDA:** ${bridge.current_ebitda:,.0f}")
                st.markdown(f"**Total Change:** ${bridge.total_change:+,.0f}")

                if bridge.is_verified:
                    st.caption("✅ Verified: components sum to total")
                else:
                    st.caption(f"⚠️ Verification delta: ${bridge.verification_delta:,.2f}")

        render_bridge(eb.mom, bridge_cols[0])
        if eb.vs_budget and len(bridge_cols) > 1:
            render_bridge(eb.vs_budget, bridge_cols[1])
        if eb.vs_prior_year and len(bridge_cols) > 2:
            render_bridge(eb.vs_prior_year, bridge_cols[2])

    tab_idx += 1


# ── Margins Tab ──
if analysis.margins:
    with tabs[tab_idx]:
        m = analysis.margins

        # Latest period metrics
        latest = m.periods[-1]
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        with mc1:
            st.metric("Gross Margin", f"{latest.gross_margin_pct:.1f}%" if latest.gross_margin_pct else "N/A")
        with mc2:
            st.metric("EBITDA Margin", f"{latest.ebitda_margin_pct:.1f}%" if latest.ebitda_margin_pct else "N/A")
        with mc3:
            st.metric("Rev Growth MoM", f"{latest.revenue_growth_mom:+.1f}%" if latest.revenue_growth_mom else "N/A")
        with mc4:
            st.metric("Rev Growth YoY", f"{latest.revenue_growth_yoy:+.1f}%" if latest.revenue_growth_yoy else "N/A")
        with mc5:
            st.metric("OpEx % Rev", f"{latest.opex_pct_revenue:.1f}%" if latest.opex_pct_revenue else "N/A")

        # Trend table
        st.subheader("Margin Trends")
        if not m.as_dataframe.empty:
            display = m.as_dataframe.copy()
            for col in display.columns:
                if col != "period" and display[col].dtype in ['float64', 'int64']:
                    display[col] = display[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            st.dataframe(display, use_container_width=True, hide_index=True)

    tab_idx += 1


# ── Variance Tab ──
if analysis.variance:
    with tabs[tab_idx]:
        var = analysis.variance

        # Show latest period
        latest_var = var.periods[-1]
        st.subheader(f"Variance Analysis — {latest_var.period}")

        var_type = st.radio("Compare against:", ["Prior Month", "Budget", "Prior Year"], horizontal=True, key="var_radio")

        var_data = None
        if var_type == "Prior Month" and latest_var.vs_prior_month:
            var_data = latest_var.vs_prior_month
        elif var_type == "Budget" and latest_var.vs_budget:
            var_data = latest_var.vs_budget
        elif var_type == "Prior Year" and latest_var.vs_prior_year:
            var_data = latest_var.vs_prior_year

        if var_data:
            rows = []
            for v in var_data:
                fav_icon = "🟢" if v.favorable == Favorability.FAVORABLE else ("🔴" if v.favorable == Favorability.UNFAVORABLE else "⚪")
                rows.append({
                    "": fav_icon,
                    "Line Item": v.line_item.replace("_", " ").title(),
                    "Actual": f"${v.actual:,.0f}",
                    "Comparator": f"${v.comparator:,.0f}",
                    "$ Change": f"${v.dollar_change:+,.0f}",
                    "% Change": f"{v.pct_change:+.1f}%" if v.pct_change is not None else "N/A",
                    "% of Revenue": f"{v.as_pct_of_revenue:.1f}%" if v.as_pct_of_revenue is not None else "N/A",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info(f"No {var_type.lower()} data available for this period.")

    tab_idx += 1


# ── Working Capital Tab ──
if analysis.working_capital:
    with tabs[tab_idx]:
        wc = analysis.working_capital

        latest_wc = wc.periods[-1]
        wc1, wc2, wc3, wc4 = st.columns(4)
        with wc1:
            st.metric("DSO", f"{latest_wc.dso:.0f} days" if latest_wc.dso else "N/A",
                      f"{latest_wc.dso - wc.periods[-2].dso:+.0f}" if len(wc.periods) > 1 and latest_wc.dso and wc.periods[-2].dso else None)
        with wc2:
            st.metric("DPO", f"{latest_wc.dpo:.0f} days" if latest_wc.dpo else "N/A")
        with wc3:
            st.metric("DIO", f"{latest_wc.dio:.0f} days" if latest_wc.dio else "N/A")
        with wc4:
            st.metric("Cash Cycle", f"{latest_wc.ccc:.0f} days" if latest_wc.ccc else "N/A")

        if latest_wc.wc_change is not None:
            direction = "consumed" if latest_wc.wc_change > 0 else "freed"
            st.info(f"Working capital change: **${abs(latest_wc.wc_change):,.0f} {direction}** this period")

        if latest_wc.dso_cash_impact is not None:
            dso_dir = "freed" if latest_wc.dso_cash_impact > 0 else "consumed"
            st.info(f"DSO cash impact: **${abs(latest_wc.dso_cash_impact):,.0f} {dso_dir}** from DSO change")

        # AR aging
        if latest_wc.ar_aging:
            st.subheader("AR Aging Distribution")
            ag = latest_wc.ar_aging
            aging_data = pd.DataFrame([{
                "Current (0-30)": f"{ag.current_pct:.1f}%" if ag.current_pct else "",
                "31-60 Days": f"{ag.pct_31_60:.1f}%" if ag.pct_31_60 else "",
                "61-90 Days": f"{ag.pct_61_90:.1f}%" if ag.pct_61_90 else "",
                "91-120 Days": f"{ag.pct_91_120:.1f}%" if ag.pct_91_120 else "",
                "120+ Days": f"{ag.over_120_pct:.1f}%" if ag.over_120_pct else "",
            }])
            st.dataframe(aging_data, use_container_width=True, hide_index=True)

        # Trend table
        st.subheader("Working Capital Trends")
        wc_rows = []
        for p in wc.periods:
            wc_rows.append({
                "Period": p.period,
                "DSO": f"{p.dso:.0f}" if p.dso else "",
                "DPO": f"{p.dpo:.0f}" if p.dpo else "",
                "DIO": f"{p.dio:.0f}" if p.dio else "",
                "CCC": f"{p.ccc:.0f}" if p.ccc else "",
                "WC Change": f"${p.wc_change:+,.0f}" if p.wc_change is not None else "",
            })
        st.dataframe(pd.DataFrame(wc_rows), use_container_width=True, hide_index=True)

    tab_idx += 1


# ── FCF Tab ──
if analysis.fcf:
    with tabs[tab_idx]:
        fcf = analysis.fcf

        latest_fcf = fcf.periods[-1]
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("Free Cash Flow",
                      f"${latest_fcf.free_cash_flow:,.0f}" if latest_fcf.free_cash_flow else "N/A")
        with fc2:
            st.metric("Cash Conversion",
                      f"{latest_fcf.cash_conversion_ratio:.1%}" if latest_fcf.cash_conversion_ratio else "N/A")
        with fc3:
            if latest_fcf.net_debt_to_ltm_ebitda is not None:
                st.metric("Net Debt / EBITDA", f"{latest_fcf.net_debt_to_ltm_ebitda:.1f}x")
            else:
                st.metric("Net Debt / EBITDA", "N/A")

        # Trend table
        st.subheader("FCF Trends")
        fcf_rows = []
        for p in fcf.periods:
            fcf_rows.append({
                "Period": p.period,
                "FCF": f"${p.free_cash_flow:,.0f}" if p.free_cash_flow else "",
                "Cash Conv.": f"{p.cash_conversion_ratio:.1%}" if p.cash_conversion_ratio else "",
                "Net Debt": f"${p.net_debt:,.0f}" if p.net_debt is not None else "",
                "ND/EBITDA": f"{p.net_debt_to_ltm_ebitda:.1f}x" if p.net_debt_to_ltm_ebitda else "",
            })
        st.dataframe(pd.DataFrame(fcf_rows), use_container_width=True, hide_index=True)

    tab_idx += 1


# ── Revenue Analytics Tab ──
if analysis.revenue_analytics:
    with tabs[tab_idx]:
        ra = analysis.revenue_analytics

        if ra.concentration:
            st.subheader("Revenue Concentration")
            latest_c = ra.concentration[-1]
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                st.metric("Top 1", f"{latest_c.top1_pct:.1f}%" if latest_c.top1_pct else "N/A")
            with rc2:
                st.metric("Top 5", f"{latest_c.top5_pct:.1f}%" if latest_c.top5_pct else "N/A")
            with rc3:
                st.metric(f"By {latest_c.dimension.title()}", f"{latest_c.count} total")
            with rc4:
                hhi_label = "Low" if latest_c.herfindahl < 0.15 else ("Moderate" if latest_c.herfindahl < 0.25 else "High")
                st.metric("HHI Concentration", f"{latest_c.herfindahl:.3f} ({hhi_label})")

        if ra.price_volume:
            st.subheader("Price / Volume / Mix Decomposition")
            pv_rows = []
            for pv in ra.price_volume:
                pv_rows.append({
                    "Period": pv.period,
                    "Price Effect": f"${pv.price_effect:+,.0f}",
                    "Volume Effect": f"${pv.volume_effect:+,.0f}",
                    "Mix Effect": f"${pv.mix_effect:+,.0f}",
                    "Total Change": f"${pv.total_change:+,.0f}",
                    "Verified": "✅" if pv.is_verified else "❌",
                })
            st.dataframe(pd.DataFrame(pv_rows), use_container_width=True, hide_index=True)

        if ra.kpi_trends:
            st.subheader("KPI Trends")
            for metric_name, series in ra.kpi_trends.items():
                display_name = metric_name.replace("_", " ").title()
                kpi_df = pd.DataFrame(series, columns=["Period", display_name])
                st.line_chart(kpi_df.set_index("Period"))

    tab_idx += 1


# ── Trend Flags Tab ──
if analysis.trends:
    with tabs[tab_idx]:
        flags = analysis.trends.flags

        if not flags:
            st.success("No trend flags detected — all metrics within normal range.")
        else:
            # Summary
            crit = sum(1 for f in flags if f.severity == Severity.CRITICAL)
            warn = sum(1 for f in flags if f.severity == Severity.WARNING)
            info = sum(1 for f in flags if f.severity == Severity.INFO)

            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("🔴 Critical", crit)
            with sc2:
                st.metric("🟡 Warning", warn)
            with sc3:
                st.metric("🔵 Info", info)

            st.divider()

            # Show flags grouped by severity
            for severity, label, css_class in [
                (Severity.CRITICAL, "Critical", "flag-critical"),
                (Severity.WARNING, "Warning", "flag-warning"),
                (Severity.INFO, "Info", "flag-info"),
            ]:
                sev_flags = [f for f in flags if f.severity == severity]
                if sev_flags:
                    st.subheader(f"{label} ({len(sev_flags)})")
                    for f in sev_flags:
                        metric_display = f.metric.replace("_", " ").title()
                        type_display = f.flag_type.value.replace("_", " ").title()
                        st.markdown(
                            f'<div class="{css_class}">'
                            f'<strong>{metric_display}</strong> — {type_display}<br/>'
                            f'<span style="color:#666">{f.detail}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    tab_idx += 1


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.header("④ Export")

from analysis.excel_export import export_to_excel
from openpyxl import load_workbook
import io

# Generate Excel in memory
excel_buffer = io.BytesIO()
company = next(iter(ingested.values())).company_name if ingested else ""
export_to_excel(analysis, excel_buffer, ingested=ingested, company_name=company)
excel_bytes = excel_buffer.getvalue()

# ── Excel Preview ──
st.subheader("Excel Preview")

preview_wb = load_workbook(io.BytesIO(excel_bytes))
preview_tabs = st.tabs(preview_wb.sheetnames)

for i, sheet_name in enumerate(preview_wb.sheetnames):
    with preview_tabs[i]:
        ws = preview_wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append([str(v) if v is not None else "" for v in row])
        if rows:
            preview_df = pd.DataFrame(rows[1:], columns=rows[0]) if len(rows) > 1 else pd.DataFrame(rows)
            st.dataframe(preview_df, use_container_width=True, hide_index=True, height=350)
        else:
            st.info("Empty sheet")

st.divider()

st.download_button(
    "📥 Download Excel Workbook",
    excel_bytes,
    file_name=f"analysis_{date.today().isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
