"""
PE Value Creation Platform

Clean workflow: Company → Upload → Analyze → Assumptions → Research → Export
Run with: streamlit run app.py
"""

import io
import os
import tempfile
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PE Value Creation", page_icon="📊", layout="wide")

# ── Imports (lazy to keep startup fast) ──
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
# SIDEBAR — Company Selection
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### Portfolio")

    # Demo companies
    demo_companies = {
        "Meridian Software": {
            "sector": "B2B SaaS",
            "files": {
                "P&L": "data/sample_pl.csv",
                "Balance Sheet": "data/test/balance_sheet_clean.csv",
                "Cash Flow": "data/test/cash_flow_clean.csv",
                "Working Capital": "data/test/working_capital_clean.csv",
                "Revenue Detail": "data/test/revenue_detail_clean.csv",
                "KPIs": "data/test/kpi_operational_clean.csv",
            }
        },
        "Atlas Manufacturing": {
            "sector": "Manufacturing",
            "files": {
                "P&L": "data/test/manufacturing_pl.xlsx",
            }
        },
        "Acme Corp": {
            "sector": "B2B SaaS",
            "files": {
                "P&L": "data/test/quickbooks_export.csv",
            }
        },
    }

    company = st.selectbox("Company", list(demo_companies.keys()) + ["+ New Company"])

    if company == "+ New Company":
        company = st.text_input("Company Name")
        sector = st.selectbox("Sector", ["B2B SaaS", "Manufacturing", "Services", "Healthcare", "Distribution", "Retail", "Other"])
        uploaded = st.file_uploader("Upload Financial Data", type=["csv", "xlsx", "xls", "pdf"], accept_multiple_files=True)
    else:
        sector = demo_companies[company]["sector"]
        uploaded = None

    st.divider()
    st.caption(f"**{company}** · {sector}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Clean workflow
# ═══════════════════════════════════════════════════════════════════════════

st.title(company or "PE Value Creation")
st.caption(sector)

# ── Step 1: Load Data ──

if "loaded_company" not in st.session_state or st.session_state.get("loaded_company") != company:
    # Load data for this company
    ingested = {}

    if company in demo_companies:
        for label, path in demo_companies[company]["files"].items():
            try:
                r = ingest_file(path, company_name=company, business_type=sector)
                ingested[r.doc_type] = r
            except Exception:
                pass
    elif uploaded:
        for f in uploaded:
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
        st.session_state["loaded_company"] = company
        st.session_state["suggested"] = suggest_assumptions(ingested)

if "ingested" not in st.session_state:
    st.info("Select a company from the sidebar to get started.")
    st.stop()

ingested = st.session_state["ingested"]
suggested = st.session_state["suggested"]

# Data summary bar
doc_types = [r.doc_type_name.split("/")[0].strip()[:15] for r in ingested.values()]
total_rows = sum(len(r.df) for r in ingested.values())
st.caption(f"📂 {len(ingested)} documents loaded · {total_rows} rows · {', '.join(doc_types)}")

st.divider()

# ── Step 2: Assumptions ──

with st.expander("⚙️ Assumptions", expanded=False):
    st.caption("Auto-generated from historical data. Edit to update projections.")

    ac1, ac2, ac3 = st.columns(3)

    with ac1:
        rev_growth = st.number_input("Revenue Growth (% MoM)", value=suggested.revenue.growth_rate_pct or 0.0, step=0.5, format="%.1f")
        proj_months = st.number_input("Projection Months", value=12, min_value=1, max_value=60, step=6)

    with ac2:
        def _pct(item):
            for cl in suggested.costs.lines:
                if cl.line_item == item:
                    return cl.pct_of_revenue or 0.0
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
    color = "green" if implied > 10 else ("orange" if implied > 0 else "red")
    st.markdown(f"Implied EBITDA Margin: :{color}[**{implied:.1f}%**]")

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
    capex=suggested.capex,
    debt=suggested.debt,
    tax=suggested.tax,
    exit_=ExitAssumptions(exit_year=5, exit_multiple=exit_mult, entry_equity=entry_eq * 1e6),
)

# ── Step 3: Run Model ──

model = run_model(ingested, assumptions)
analysis = model.analysis

# ── Key Metrics Banner ──

m1, m2, m3, m4, m5, m6 = st.columns(6)

if analysis.ltm:
    ltm = analysis.ltm
    with m1:
        st.metric("LTM Revenue", f"${ltm.ltm_revenue/1e6:.1f}M" if ltm.ltm_revenue else "—")
    with m2:
        st.metric("LTM EBITDA", f"${ltm.ltm_ebitda/1e6:.1f}M" if ltm.ltm_ebitda else "—")
    with m3:
        st.metric("EBITDA Margin", f"{ltm.ltm_ebitda_margin_pct:.1f}%" if ltm.ltm_ebitda_margin_pct else "—")
    with m4:
        st.metric("Rule of 40", f"{ltm.rule_of_40:.0f}" if ltm.rule_of_40 else "—")

if model.returns and model.returns.moic:
    with m5:
        st.metric("MOIC", f"{model.returns.moic:.2f}x")
    with m6:
        st.metric("IRR", f"{model.returns.irr:.0%}" if model.returns.irr else "—")

st.divider()

# ── Step 4: Analysis Tabs ──

tab_names = []
if analysis.ebitda_bridges: tab_names.append("EBITDA Bridge")
if analysis.margins: tab_names.append("Margins")
if analysis.variance: tab_names.append("Variance")
if analysis.working_capital: tab_names.append("Working Capital")
if analysis.fcf: tab_names.append("FCF")
if analysis.ltm: tab_names.append("LTM")
if analysis.revenue_analytics: tab_names.append("Revenue")
if analysis.trends: tab_names.append("Flags")
tab_names.append("Forecast")
tab_names.append("Export")

tabs = st.tabs(tab_names)
ti = 0

# ── EBITDA Bridge ──
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
                    clr = "green" if c.value >= 0 else "red"
                    st.markdown(f":{clr}[{c.name}: ${c.value:+,.0f}]")
                st.markdown(f"Ending: **${b.current_ebitda:,.0f}** (Δ ${b.total_change:+,.0f})")
                st.caption("✅ Verified" if b.is_verified else "⚠️ Check")

        _bridge(eb.mom, cols[0])
        if eb.vs_budget and len(cols) > 1: _bridge(eb.vs_budget, cols[1])
        if eb.vs_prior_year and len(cols) > 2: _bridge(eb.vs_prior_year, cols[2])
    ti += 1

# ── Margins ──
if analysis.margins:
    with tabs[ti]:
        if not analysis.margins.as_dataframe.empty:
            df = analysis.margins.as_dataframe.copy()
            for c in df.columns:
                if c != "period" and df[c].dtype in ["float64"]:
                    df[c] = df[c].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            st.dataframe(df, use_container_width=True, hide_index=True)
    ti += 1

# ── Variance ──
if analysis.variance:
    with tabs[ti]:
        lv = analysis.variance.periods[-1]
        data = lv.vs_prior_month
        if data:
            rows = []
            for v in data:
                f = "🟢" if v.favorable == Favorability.FAVORABLE else ("🔴" if v.favorable == Favorability.UNFAVORABLE else "⚪")
                rows.append({"": f, "Line": v.line_item.replace("_", " ").title(), "Actual": f"${v.actual:,.0f}", "Prior": f"${v.comparator:,.0f}", "Change": f"${v.dollar_change:+,.0f}", "%": f"{v.pct_change:+.1f}%" if v.pct_change else ""})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    ti += 1

# ── Working Capital ──
if analysis.working_capital:
    with tabs[ti]:
        wc = analysis.working_capital
        rows = [{"Period": p.period, "DSO": f"{p.dso:.0f}" if p.dso else "", "DPO": f"{p.dpo:.0f}" if p.dpo else "", "CCC": f"{p.ccc:.0f}" if p.ccc else "", "WC Chg": f"${p.wc_change:+,.0f}" if p.wc_change is not None else ""} for p in wc.periods]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    ti += 1

# ── FCF ──
if analysis.fcf:
    with tabs[ti]:
        rows = [{"Period": p.period, "FCF": f"${p.free_cash_flow:,.0f}" if p.free_cash_flow else "", "Cash Conv": f"{p.cash_conversion_ratio:.0%}" if p.cash_conversion_ratio else "", "ND/EBITDA": f"{p.net_debt_to_ltm_ebitda:.1f}x" if p.net_debt_to_ltm_ebitda else ""} for p in analysis.fcf.periods]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    ti += 1

# ── LTM ──
if analysis.ltm:
    with tabs[ti]:
        l = analysis.ltm
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("LTM Revenue", f"${l.ltm_revenue:,.0f}" if l.ltm_revenue else "—")
        with c2: st.metric("LTM EBITDA", f"${l.ltm_ebitda:,.0f}" if l.ltm_ebitda else "—")
        with c3: st.metric("Margin", f"{l.ltm_ebitda_margin_pct:.1f}%" if l.ltm_ebitda_margin_pct else "—")
        with c4:
            if l.rule_of_40 is not None:
                clr = "green" if l.rule_of_40 >= 40 else "red"
                st.metric("Rule of 40", f":{clr}[{l.rule_of_40:.0f}]")
    ti += 1

# ── Revenue ──
if analysis.revenue_analytics:
    with tabs[ti]:
        ra = analysis.revenue_analytics
        if ra.concentration:
            c = ra.concentration[-1]
            st.caption(f"By {c.dimension} · {c.count} total · HHI: {c.herfindahl:.3f}")
        if ra.price_volume:
            rows = [{"Period": p.period, "Price": f"${p.price_effect:+,.0f}", "Volume": f"${p.volume_effect:+,.0f}", "Mix": f"${p.mix_effect:+,.0f}", "Total": f"${p.total_change:+,.0f}"} for p in ra.price_volume]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    ti += 1

# ── Flags ──
if analysis.trends:
    with tabs[ti]:
        flags = analysis.trends.flags
        if not flags:
            st.success("No flags — all metrics normal.")
        else:
            for f in sorted(flags, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity.value, 3)):
                icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(f.severity.value, "⚪")
                st.markdown(f"{icon} **{f.metric.replace('_', ' ').title()}** — {f.detail}")
    ti += 1

# ── Forecast ──
with tabs[ti]:
    if "income_statement" in model.combined_data:
        df = model.combined_data["income_statement"].df.copy()
        pcol = "period" if "period" in df.columns else "month"
        df["Type"] = df["_is_projected"].apply(lambda x: "Projected" if x else "Actual")
        display = df[[pcol, "Type", "revenue", "cogs", "gross_profit", "ebitda"]].copy()
        for c in ["revenue", "cogs", "gross_profit", "ebitda"]:
            display[c] = display[c].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
        st.dataframe(display, use_container_width=True, hide_index=True, height=400)
ti += 1

# ── Export ──
with tabs[ti]:
    from openpyxl import load_workbook

    buf = io.BytesIO()
    export_to_excel(analysis, buf, ingested=model.combined_data, company_name=company)
    excel_bytes = buf.getvalue()

    # Preview
    wb = load_workbook(io.BytesIO(excel_bytes))
    preview_tabs = st.tabs(wb.sheetnames)
    for i, name in enumerate(wb.sheetnames):
        with preview_tabs[i]:
            ws = wb[name]
            rows = [[str(v) if v is not None else "" for v in row] for row in ws.iter_rows(values_only=True)]
            if rows:
                nc = max(len(r) for r in rows)
                padded = [r + [""] * (nc - len(r)) for r in rows]
                st.dataframe(pd.DataFrame(padded, columns=[f"Col {j+1}" for j in range(nc)]), use_container_width=True, hide_index=True, height=300)

    st.download_button("📥 Download Excel", excel_bytes, file_name=f"{company}_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
