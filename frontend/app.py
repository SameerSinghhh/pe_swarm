"""
PE Value Creation Platform

Company → Upload → Analyze → Chat with AI Analyst
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


def _fmt(val):
    if val is None: return "—"
    if abs(val) >= 1e9: return f"${val/1e9:.1f}B"
    if abs(val) >= 1e6: return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3: return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### Portfolio")

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

    company = st.selectbox("Company", list(demo_companies.keys()) + ["+ New Company"])
    if company == "+ New Company":
        company = st.text_input("Company Name")
        sector = st.selectbox("Sector", ["B2B SaaS", "Manufacturing", "Services", "Healthcare", "Distribution", "Retail"])
    else:
        sector = demo_companies[company]["sector"]

    st.divider()
    uploaded_files = st.file_uploader("Upload Documents", type=["csv", "xlsx", "xls", "pdf"], accept_multiple_files=True)
    st.caption("P&L, Balance Sheet, Cash Flow, AR/AP, Revenue, KPIs")

    st.divider()
    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

st.title(company or "PE Value Creation")

# ── INGEST ──

if run_btn:
    ingested = {}
    use_demo = (company in demo_companies) and not uploaded_files
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
        suggested = suggest_assumptions(ingested)
        # Build default assumptions
        def _pct(item):
            for cl in suggested.costs.lines:
                if cl.line_item == item: return cl.pct_of_revenue or 0.0
            return 0.0

        assumptions = AssumptionSet(
            projection_months=12,
            revenue=RevenueAssumptions(method="growth_rate", growth_rate_pct=suggested.revenue.growth_rate_pct or 0),
            costs=CostAssumptions(lines=[
                CostLineAssumption("cogs", method="pct_of_revenue", pct_of_revenue=_pct("cogs")),
                CostLineAssumption("sales_marketing", method="pct_of_revenue", pct_of_revenue=_pct("sales_marketing")),
                CostLineAssumption("rd", method="pct_of_revenue", pct_of_revenue=_pct("rd")),
                CostLineAssumption("ga", method="pct_of_revenue", pct_of_revenue=_pct("ga")),
            ]),
            working_capital=WorkingCapitalAssumptions(
                target_dso=suggested.working_capital.target_dso or 40,
                target_dpo=suggested.working_capital.target_dpo or 30,
            ),
            capex=suggested.capex, debt=suggested.debt, tax=suggested.tax,
            exit_=ExitAssumptions(exit_year=5, exit_multiple=10.0, entry_equity=10_000_000),
        )

        model = run_model(ingested, assumptions)

        st.session_state["ingested"] = ingested
        st.session_state["assumptions"] = assumptions
        st.session_state["model"] = model
        st.session_state["analysis"] = model.analysis
        st.session_state["company"] = company
        st.session_state["sector"] = sector
        st.session_state["ready"] = True
        st.session_state["chat_history"] = []

if not st.session_state.get("ready"):
    st.info("Select a company and click **Run Analysis** to get started.")
    st.stop()

analysis = st.session_state["analysis"]
model = st.session_state["model"]
ingested = st.session_state["ingested"]

# ── KEY METRICS ──

mc = st.columns(6)
if analysis.ltm:
    l = analysis.ltm
    with mc[0]: st.metric("LTM Revenue", _fmt(l.ltm_revenue))
    with mc[1]: st.metric("LTM EBITDA", _fmt(l.ltm_ebitda))
    with mc[2]: st.metric("EBITDA Margin", f"{l.ltm_ebitda_margin_pct:.1f}%" if l.ltm_ebitda_margin_pct else "—")
    with mc[3]: st.metric("Rule of 40", f"{l.rule_of_40:.0f}" if l.rule_of_40 else "—")
if model.returns and model.returns.moic:
    with mc[4]: st.metric("MOIC", f"{model.returns.moic:.2f}x")
    with mc[5]: st.metric("IRR", f"{model.returns.irr:.0%}" if model.returns.irr else "—")

# Excel download
buf = io.BytesIO()
export_data = {}
for dt, nr in model.combined_data.items():
    export_data[dt] = NormalizedResult(df=nr.df, doc_type=nr.doc_type, doc_type_name=nr.doc_type_name,
                                       quality_score=ingested[dt].quality_score if dt in ingested else 0)
export_to_excel(analysis, buf, ingested=export_data, company_name=company)
st.download_button("📥 Excel", buf.getvalue(), file_name=f"{company}_{date.today()}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── ANALYSIS TABS ──

tab_names = []
if analysis.ebitda_bridges: tab_names.append("Bridge")
if analysis.margins: tab_names.append("Margins")
if analysis.variance: tab_names.append("Variance")
if analysis.working_capital: tab_names.append("WC")
if analysis.fcf: tab_names.append("FCF")
if analysis.revenue_analytics: tab_names.append("Revenue")
if analysis.trends: tab_names.append("Flags")

if tab_names:
    tabs = st.tabs(tab_names)
    ti = 0

    if analysis.ebitda_bridges:
        with tabs[ti]:
            eb = analysis.ebitda_bridges
            if eb.mom:
                b = eb.mom
                rows = [["Starting EBITDA", _fmt(b.base_ebitda)]]
                for c in b.components:
                    sign = "+" if c.value >= 0 else ""
                    rows.append([f"  {c.name}", f"{sign}{_fmt(c.value)}"])
                rows.append(["Ending EBITDA", _fmt(b.current_ebitda)])
                rows.append(["Total Change", f"{'+'if b.total_change>=0 else ''}{_fmt(b.total_change)}"])
                st.dataframe(pd.DataFrame(rows, columns=["Component", "Amount"]), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.margins:
        with tabs[ti]:
            df = analysis.margins.as_dataframe.copy()
            for c in df.columns:
                if c != "period" and df[c].dtype in ["float64"]:
                    df[c] = df[c].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            st.dataframe(df, use_container_width=True, hide_index=True)
        ti += 1

    if analysis.variance:
        with tabs[ti]:
            lv = analysis.variance.periods[-1]
            data = lv.vs_prior_month
            if data:
                rows = [{"Line": v.line_item.replace("_"," ").title(), "Actual": _fmt(v.actual), "Prior": _fmt(v.comparator), "Change": f"{'+'if v.dollar_change>=0 else ''}{_fmt(v.dollar_change)}", "%": f"{v.pct_change:+.1f}%" if v.pct_change else ""} for v in data]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.working_capital:
        with tabs[ti]:
            rows = [{"Period": p.period, "DSO": f"{p.dso:.0f}" if p.dso else "", "DPO": f"{p.dpo:.0f}" if p.dpo else "", "CCC": f"{p.ccc:.0f}" if p.ccc else ""} for p in analysis.working_capital.periods]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.fcf:
        with tabs[ti]:
            rows = [{"Period": p.period, "FCF": _fmt(p.free_cash_flow), "Cash Conv": f"{p.cash_conversion_ratio:.0%}" if p.cash_conversion_ratio else ""} for p in analysis.fcf.periods]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.revenue_analytics:
        with tabs[ti]:
            ra = analysis.revenue_analytics
            if ra.concentration:
                c = ra.concentration[-1]
                st.caption(f"By {c.dimension} · {c.count} total · HHI: {c.herfindahl:.3f}")
        ti += 1

    if analysis.trends:
        with tabs[ti]:
            flags = analysis.trends.flags
            if not flags:
                st.success("No flags.")
            else:
                for f in sorted(flags, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity.value, 3)):
                    icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(f.severity.value, "⚪")
                    st.caption(f"{icon} {f.metric.replace('_',' ').title()}: {f.detail}")
        ti += 1

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# CHAT INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("### 💬 AI Analyst")
st.caption("Ask anything about the company. The AI calls real analysis tools — never makes up numbers.")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Display chat history
for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about the company..."):
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build context for the agent
    chat_context = {
        "analysis": analysis,
        "ingested": ingested,
        "assumptions": st.session_state.get("assumptions"),
        "model": model,
        "research": st.session_state.get("research"),
        "company_name": st.session_state.get("company", company),
        "sector": st.session_state.get("sector", sector),
    }

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            from chat.agent import chat as agent_chat
            response, updated_history = agent_chat(
                prompt,
                st.session_state["chat_history"],
                chat_context,
            )
            st.markdown(response)

    # Update session state with the full history from the agent
    st.session_state["chat_history"] = updated_history
