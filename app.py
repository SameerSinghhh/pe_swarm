"""
PE Value Creation Platform

Company → Upload → Analyze → Research → Value Creation
Run with: streamlit run app.py
"""

import io
import os
import tempfile
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PE Value Creation", page_icon="📊", layout="wide")

from core.ingest import ingest_file
from core.result import NormalizedResult
from analysis.engine import run_analysis
from analysis.types import Favorability, Severity
from analysis.excel_export import export_to_excel
from modeling.types import (
    AssumptionSet, RevenueAssumptions, CostAssumptions, CostLineAssumption,
    WorkingCapitalAssumptions, ExitAssumptions,
)
from modeling.auto_suggest import suggest_assumptions
from modeling.engine import run_model


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### Portfolio Companies")

    demo_companies = {
        "Meridian Software": {"sector": "B2B SaaS", "files": {
            "P&L": "data/sample_pl.csv",
            "Balance Sheet": "data/test/balance_sheet_clean.csv",
            "Cash Flow": "data/test/cash_flow_clean.csv",
            "Working Capital": "data/test/working_capital_clean.csv",
            "Revenue Detail": "data/test/revenue_detail_clean.csv",
            "KPIs": "data/test/kpi_operational_clean.csv",
        }},
        "Atlas Manufacturing": {"sector": "Manufacturing", "files": {"P&L": "data/test/manufacturing_pl.xlsx"}},
        "Acme Corp": {"sector": "B2B SaaS", "files": {"P&L": "data/test/quickbooks_export.csv"}},
    }

    company = st.selectbox("Select Company", list(demo_companies.keys()) + ["+ New Company"])

    if company == "+ New Company":
        company = st.text_input("Company Name")
        sector = st.selectbox("Sector", ["B2B SaaS", "Manufacturing", "Services", "Healthcare", "Distribution", "Retail"])
    else:
        sector = demo_companies[company]["sector"]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

st.title(company or "PE Value Creation Platform")
st.caption(f"{sector}")

# ── Upload & Run Section ──

st.markdown("### 1. Upload Documents")
st.caption("Upload any financial files — P&L, Balance Sheet, Cash Flow, Working Capital, Revenue Detail, KPIs. Supports CSV, Excel, and PDF. The system auto-detects the document type and normalizes the data.")

upload_col, info_col = st.columns([2, 1])

with upload_col:
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["csv", "xlsx", "xls", "pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

with info_col:
    st.markdown("""
    **Supported formats:**
    - Monthly P&L / Income Statement
    - Balance Sheet
    - Cash Flow Statement
    - AR/AP Aging Reports
    - Revenue by Customer/Product
    - KPI / Operational Metrics
    """)

# Determine which files to use
use_demo = (company in demo_companies) and not uploaded_files

if use_demo:
    st.info(f"Using demo data for **{company}**. Upload your own files to replace.")

run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

# ── Ingest ──

if run_btn or st.session_state.get("analysis_ready"):
    if run_btn:
        ingested = {}
        if use_demo:
            for label, path in demo_companies[company]["files"].items():
                try:
                    r = ingest_file(path, company_name=company, business_type=sector)
                    ingested[r.doc_type] = r
                except Exception:
                    pass
        elif uploaded_files:
            for f in uploaded_files:
                suffix = os.path.splitext(f.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(f.read())
                try:
                    r = ingest_file(tmp.name, company_name=company, business_type=sector)
                    ingested[r.doc_type] = r
                except Exception:
                    pass

        if ingested:
            st.session_state["ingested"] = ingested
            st.session_state["suggested"] = suggest_assumptions(ingested)
            st.session_state["analysis_ready"] = True
            st.session_state["company"] = company
        else:
            st.warning("No data loaded. Select a demo company or upload files.")
            st.stop()

    if not st.session_state.get("analysis_ready"):
        st.stop()

    ingested = st.session_state["ingested"]
    suggested = st.session_state["suggested"]

    # Data loaded bar
    doc_names = [r.doc_type_name.split("/")[0].strip() for r in ingested.values()]
    st.success(f"**{len(ingested)} documents loaded:** {', '.join(doc_names)}")

    st.divider()

    # ── Assumptions ──

    st.markdown("### 2. Assumptions")
    st.caption("Auto-generated from your data. Adjust to model scenarios.")

    with st.expander("Edit Assumptions", expanded=False):
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            rev_growth = st.number_input("Revenue Growth (% MoM)", value=suggested.revenue.growth_rate_pct or 0.0, step=0.5, format="%.1f")
            proj_months = st.number_input("Projection Months", value=12, min_value=1, max_value=60, step=6)
        with ac2:
            def _pct(item):
                for cl in suggested.costs.lines:
                    if cl.line_item == item: return cl.pct_of_revenue or 0.0
                return 0.0
            cogs_pct = st.number_input("COGS %", value=_pct("cogs"), step=0.5, format="%.1f")
            sm_pct = st.number_input("S&M %", value=_pct("sales_marketing"), step=0.5, format="%.1f")
            rd_pct = st.number_input("R&D %", value=_pct("rd"), step=0.5, format="%.1f")
            ga_pct = st.number_input("G&A %", value=_pct("ga"), step=0.5, format="%.1f")
        with ac3:
            dso = st.number_input("Target DSO", value=suggested.working_capital.target_dso or 40.0, step=1.0, format="%.0f")
            dpo = st.number_input("Target DPO", value=suggested.working_capital.target_dpo or 30.0, step=1.0, format="%.0f")
            exit_mult = st.number_input("Exit Multiple", value=10.0, step=0.5, format="%.1f")
            entry_eq = st.number_input("Entry Equity ($M)", value=10.0, step=1.0, format="%.1f")

        implied = 100 - cogs_pct - sm_pct - rd_pct - ga_pct
        if implied > 10:
            st.markdown(f"Implied EBITDA Margin: **{implied:.1f}%**")
        elif implied > 0:
            st.markdown(f"Implied EBITDA Margin: **{implied:.1f}%** ⚠️")
        else:
            st.markdown(f"Implied EBITDA Margin: **{implied:.1f}%** 🔴")

    # Build assumptions
    assumptions = AssumptionSet(
        projection_months=proj_months,
        revenue=RevenueAssumptions(method="growth_rate", growth_rate_pct=rev_growth),
        costs=CostAssumptions(lines=[
            CostLineAssumption("cogs", method="pct_of_revenue", pct_of_revenue=cogs_pct),
            CostLineAssumption("sales_marketing", method="pct_of_revenue", pct_of_revenue=sm_pct),
            CostLineAssumption("rd", method="pct_of_revenue", pct_of_revenue=rd_pct),
            CostLineAssumption("ga", method="pct_of_revenue", pct_of_revenue=ga_pct),
        ]),
        working_capital=WorkingCapitalAssumptions(target_dso=dso, target_dpo=dpo),
        capex=suggested.capex, debt=suggested.debt, tax=suggested.tax,
        exit_=ExitAssumptions(exit_year=5, exit_multiple=exit_mult, entry_equity=entry_eq * 1e6),
    )

    # Run model
    model = run_model(ingested, assumptions)
    analysis = model.analysis

    st.divider()

    # ── Key Metrics ──

    st.markdown("### 3. Analysis")

    mc = st.columns(6)
    if analysis.ltm:
        l = analysis.ltm
        with mc[0]: st.metric("LTM Revenue", f"${l.ltm_revenue/1e6:.1f}M" if l.ltm_revenue else "—")
        with mc[1]: st.metric("LTM EBITDA", f"${l.ltm_ebitda/1e6:.1f}M" if l.ltm_ebitda else "—")
        with mc[2]: st.metric("EBITDA Margin", f"{l.ltm_ebitda_margin_pct:.1f}%" if l.ltm_ebitda_margin_pct else "—")
        with mc[3]:
            r40 = l.rule_of_40
            if r40 is not None:
                st.metric("Rule of 40", f"{r40:.0f}")
            else:
                st.metric("Rule of 40", "—")
    if model.returns and model.returns.moic:
        with mc[4]: st.metric("MOIC", f"{model.returns.moic:.2f}x")
        with mc[5]: st.metric("IRR", f"{model.returns.irr:.0%}" if model.returns.irr else "—")

    # ── Analysis Tabs ──

    tab_names = []
    if analysis.ebitda_bridges: tab_names.append("EBITDA Bridge")
    if analysis.margins: tab_names.append("Margins")
    if analysis.variance: tab_names.append("Variance")
    if analysis.working_capital: tab_names.append("Working Capital")
    if analysis.fcf: tab_names.append("FCF")
    if analysis.revenue_analytics: tab_names.append("Revenue")
    if analysis.trends: tab_names.append("Flags")
    tab_names.append("Forecast")

    tabs = st.tabs(tab_names)
    ti = 0

    # Helper: per-tab export button
    def _tab_export(tab_name, df):
        csv = df.to_csv(index=False)
        st.download_button(f"📥 Export {tab_name}", csv, file_name=f"{company}_{tab_name}_{date.today()}.csv", mime="text/csv")

    # EBITDA Bridge
    if analysis.ebitda_bridges:
        with tabs[ti]:
            eb = analysis.ebitda_bridges
            cols = st.columns(3 if eb.vs_prior_year else (2 if eb.vs_budget else 1))
            def _bridge(b, col):
                if not b: return
                with col:
                    st.markdown(f"**{b.label}** ({b.base_period} → {b.current_period})")
                    st.markdown(f"Starting: **${b.base_ebitda:,.0f}**")
                    for c in b.components:
                        color = "green" if c.value >= 0 else "red"
                        st.markdown(f":{color}[{c.name}: ${c.value:+,.0f}]")
                    st.markdown(f"Ending: **${b.current_ebitda:,.0f}** (Δ ${b.total_change:+,.0f})")
                    st.caption("✅ Verified" if b.is_verified else "⚠️ Check")
            _bridge(eb.mom, cols[0])
            if eb.vs_budget and len(cols) > 1: _bridge(eb.vs_budget, cols[1])
            if eb.vs_prior_year and len(cols) > 2: _bridge(eb.vs_prior_year, cols[2])
        ti += 1

    # Margins
    if analysis.margins:
        with tabs[ti]:
            if not analysis.margins.as_dataframe.empty:
                df = analysis.margins.as_dataframe.copy()
                for c in df.columns:
                    if c != "period" and df[c].dtype in ["float64"]:
                        df[c] = df[c].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                st.dataframe(df, use_container_width=True, hide_index=True)
                _tab_export("Margins", analysis.margins.as_dataframe)
        ti += 1

    # Variance
    if analysis.variance:
        with tabs[ti]:
            lv = analysis.variance.periods[-1]
            data = lv.vs_prior_month
            if data:
                rows_data = []
                for v in data:
                    f = "🟢" if v.favorable == Favorability.FAVORABLE else ("🔴" if v.favorable == Favorability.UNFAVORABLE else "⚪")
                    rows_data.append({"": f, "Line": v.line_item.replace("_", " ").title(), "Actual": f"${v.actual:,.0f}", "Prior": f"${v.comparator:,.0f}", "Change": f"${v.dollar_change:+,.0f}", "%": f"{v.pct_change:+.1f}%" if v.pct_change else ""})
                vdf = pd.DataFrame(rows_data)
                st.dataframe(vdf, use_container_width=True, hide_index=True)
                _tab_export("Variance", vdf)
        ti += 1

    # Working Capital
    if analysis.working_capital:
        with tabs[ti]:
            wc_rows = [{"Period": p.period, "DSO": f"{p.dso:.0f}" if p.dso else "", "DPO": f"{p.dpo:.0f}" if p.dpo else "", "CCC": f"{p.ccc:.0f}" if p.ccc else "", "WC Change": f"${p.wc_change:+,.0f}" if p.wc_change is not None else ""} for p in analysis.working_capital.periods]
            wdf = pd.DataFrame(wc_rows)
            st.dataframe(wdf, use_container_width=True, hide_index=True)
            _tab_export("Working_Capital", wdf)
        ti += 1

    # FCF
    if analysis.fcf:
        with tabs[ti]:
            fcf_rows = [{"Period": p.period, "FCF": f"${p.free_cash_flow:,.0f}" if p.free_cash_flow else "", "Cash Conv": f"{p.cash_conversion_ratio:.0%}" if p.cash_conversion_ratio else "", "ND/EBITDA": f"{p.net_debt_to_ltm_ebitda:.1f}x" if p.net_debt_to_ltm_ebitda else ""} for p in analysis.fcf.periods]
            fdf = pd.DataFrame(fcf_rows)
            st.dataframe(fdf, use_container_width=True, hide_index=True)
            _tab_export("FCF", fdf)
        ti += 1

    # Revenue
    if analysis.revenue_analytics:
        with tabs[ti]:
            ra = analysis.revenue_analytics
            if ra.concentration:
                c = ra.concentration[-1]
                st.caption(f"By {c.dimension} · {c.count} total · HHI: {c.herfindahl:.3f}")
            if ra.price_volume:
                pv_rows = [{"Period": p.period, "Price": f"${p.price_effect:+,.0f}", "Volume": f"${p.volume_effect:+,.0f}", "Mix": f"${p.mix_effect:+,.0f}", "Total": f"${p.total_change:+,.0f}"} for p in ra.price_volume]
                st.dataframe(pd.DataFrame(pv_rows), use_container_width=True, hide_index=True)
        ti += 1

    # Flags
    if analysis.trends:
        with tabs[ti]:
            flags = analysis.trends.flags
            if not flags:
                st.success("No flags — all metrics within normal range.")
            else:
                for f in sorted(flags, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity.value, 3)):
                    icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(f.severity.value, "⚪")
                    st.markdown(f"{icon} **{f.metric.replace('_', ' ').title()}** — {f.detail}")
        ti += 1

    # Forecast
    with tabs[ti]:
        if "income_statement" in model.combined_data:
            df = model.combined_data["income_statement"].df.copy()
            pcol = "period" if "period" in df.columns else "month"
            df["Type"] = df["_is_projected"].apply(lambda x: "📈 Projected" if x else "📊 Actual")
            display = df[[pcol, "Type", "revenue", "cogs", "gross_profit", "ebitda"]].copy()
            for c in ["revenue", "cogs", "gross_profit", "ebitda"]:
                display[c] = display[c].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
            st.dataframe(display, use_container_width=True, hide_index=True, height=400)
            _tab_export("Forecast", model.combined_data["income_statement"].df)

    st.divider()

    # ── Full Excel Export ──

    st.markdown("### 4. Export")

    buf = io.BytesIO()
    export_to_excel(analysis, buf, ingested=model.combined_data, company_name=company)
    excel_bytes = buf.getvalue()

    st.download_button(
        "📥 Download Full Excel Workbook",
        excel_bytes,
        file_name=f"{company}_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.expander("Preview Excel"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(excel_bytes))
        ptabs = st.tabs(wb.sheetnames)
        for i, name in enumerate(wb.sheetnames):
            with ptabs[i]:
                ws = wb[name]
                rows = [[str(v) if v is not None else "" for v in row] for row in ws.iter_rows(values_only=True)]
                if rows:
                    nc = max(len(r) for r in rows)
                    padded = [r + [""] * (nc - len(r)) for r in rows]
                    st.dataframe(pd.DataFrame(padded, columns=[f"Col {j+1}" for j in range(nc)]), use_container_width=True, hide_index=True, height=250)

    st.divider()

    # ── Market Research ──

    st.markdown("### 5. Market Research")
    st.caption("External data: peer benchmarks, industry context, macro environment, recent news.")

    if st.button("🔍 Run Market Research", use_container_width=True):
        with st.spinner("Researching... (pulling peer data, industry context, news — ~30 seconds)"):
            try:
                from research.engine import run_research

                # Build company metrics from analysis
                company_metrics = {}
                if analysis.margins and analysis.margins.periods:
                    m = analysis.margins.periods[-1]
                    company_metrics = {
                        "gross_margin_pct": m.gross_margin_pct,
                        "ebitda_margin_pct": m.ebitda_margin_pct,
                        "revenue_growth_yoy_pct": m.revenue_growth_yoy,
                        "sm_pct_revenue": m.sm_pct_revenue,
                        "rd_pct_revenue": m.rd_pct_revenue,
                        "ga_pct_revenue": m.ga_pct_revenue,
                    }
                if analysis.ltm:
                    company_metrics["ltm_revenue"] = analysis.ltm.ltm_revenue
                    company_metrics["ltm_ebitda"] = analysis.ltm.ltm_ebitda

                brief = run_research(company, sector, company_metrics)
                st.session_state["research"] = brief
            except Exception as e:
                st.error(f"Research failed: {e}")

    if "research" in st.session_state:
        brief = st.session_state["research"]

        # Company Profile
        if brief.profile and brief.profile.business_description:
            st.subheader("Company Profile")
            st.write(brief.profile.business_description)
            if brief.profile.sub_sector:
                st.caption(f"Sub-sector: {brief.profile.sub_sector} · {brief.profile.revenue_bracket}")

        # Peer Comparison
        if brief.peer_companies:
            st.subheader("Peer Comparison")
            peer_rows = []
            for p in brief.peer_companies:
                rev = f"${p.revenue/1e9:.1f}B" if p.revenue and p.revenue > 1e9 else (f"${p.revenue/1e6:.0f}M" if p.revenue else "—")
                peer_rows.append({
                    "Company": f"{p.name} ({p.ticker})",
                    "Revenue": rev,
                    "Gross Margin": f"{p.gross_margin_pct:.1f}%" if p.gross_margin_pct else "—",
                    "EBITDA Margin": f"{p.ebitda_margin_pct:.1f}%" if p.ebitda_margin_pct else "—",
                    "Growth": f"{p.revenue_growth_yoy_pct:.1f}%" if p.revenue_growth_yoy_pct else "—",
                    "EV/EBITDA": f"{p.ev_to_ebitda:.1f}x" if p.ev_to_ebitda else "—",
                })
            st.dataframe(pd.DataFrame(peer_rows), use_container_width=True, hide_index=True)

        # Gap Analysis
        if brief.gaps:
            st.subheader("Gap Analysis")
            for g in brief.gaps:
                if g.gap < -2:
                    st.markdown(f"🔴 **{g.metric}**: {g.company_value:.1f}% vs peer median {g.peer_median:.1f}% ({g.gap:+.1f}pp) — {g.opportunity}")
                elif g.gap > 2:
                    st.markdown(f"🟢 **{g.metric}**: {g.company_value:.1f}% vs peer median {g.peer_median:.1f}% ({g.gap:+.1f}pp) — Strength")
                else:
                    st.markdown(f"⚪ **{g.metric}**: {g.company_value:.1f}% vs peer median {g.peer_median:.1f}% ({g.gap:+.1f}pp) — In line")

        # Macro
        if brief.macro and brief.macro.sp500_level:
            st.subheader("Macro Context")
            mc1, mc2, mc3 = st.columns(3)
            with mc1: st.metric("S&P 500", f"{brief.macro.sp500_level:,.0f}", f"{brief.macro.sp500_ytd_pct:+.1f}% YTD" if brief.macro.sp500_ytd_pct else "")
            with mc2: st.metric("10Y Treasury", f"{brief.macro.treasury_10y:.2f}%" if brief.macro.treasury_10y else "—")
            with mc3: st.metric("Sector ETF YTD", f"{brief.macro.sector_etf_ytd_pct:+.1f}%" if brief.macro.sector_etf_ytd_pct else "—")

        # Industry Context
        if brief.industry_context:
            st.subheader("Industry Context")
            st.write(brief.industry_context[:1500])

        # News
        if brief.news:
            st.subheader("Recent News")
            for n in brief.news[:6]:
                icon = {"company": "🏢", "competitor": "⚔️", "industry": "📰"}.get(n.relevance, "📰")
                st.markdown(f"{icon} **{n.title}**")
                if n.snippet:
                    st.caption(n.snippet[:150])

        # Synthesis
        if brief.synthesis:
            st.subheader("Strategic Synthesis")
            st.info(brief.synthesis)

    st.divider()

    # ── Value Creation (Phase 5 placeholder) ──

    st.markdown("### 6. Value Creation Analysis")
    st.caption("AI-powered value creation identification — coming next.")
    st.info(
        "This section will use AI agent swarms to analyze all the data above and identify "
        "specific value creation opportunities with sized EBITDA impact. "
        "Each portfolio company will have its own AI analyst that the operating partner can chat with."
    )

else:
    st.caption("Click **Run Analysis** to get started.")
