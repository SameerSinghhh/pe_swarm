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
        uploaded = st.file_uploader("Upload Financial Data", type=["csv", "xlsx", "xls", "pdf"], accept_multiple_files=True)
    else:
        sector = demo_companies[company]["sector"]
        uploaded = None

    st.divider()
    st.caption(f"**{company}** · {sector}")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(val):
    """Format dollar value without $ that breaks markdown."""
    return f"${val:,.0f}"

def _fmt_signed(val):
    """Format signed dollar value."""
    return f"+${val:,.0f}" if val >= 0 else f"-${abs(val):,.0f}"

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

st.title(company or "PE Value Creation Platform")
st.caption(sector)

# ── 1. Upload & Run ──

st.markdown("---")
st.markdown("#### Upload Documents")
st.caption("P&L, Balance Sheet, Cash Flow, AR/AP Aging, Revenue Detail, KPIs — CSV, Excel, or PDF.")

uc1, uc2 = st.columns([3, 1])
with uc1:
    uploaded_files = st.file_uploader("Drop files here", type=["csv", "xlsx", "xls", "pdf"], accept_multiple_files=True, label_visibility="collapsed")
with uc2:
    if company in demo_companies and not uploaded_files:
        st.caption("📁 Using demo data")

run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

if run_btn or st.session_state.get("ready"):
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
            st.session_state["ingested"] = ingested
            st.session_state["suggested"] = suggest_assumptions(ingested)
            st.session_state["ready"] = True
        else:
            st.warning("No data loaded.")
            st.stop()

    if not st.session_state.get("ready"):
        st.stop()

    ingested = st.session_state["ingested"]
    suggested = st.session_state["suggested"]

    doc_names = [r.doc_type_name.split("/")[0].strip() for r in ingested.values()]
    st.success(f"{len(ingested)} documents: {', '.join(doc_names)}")

    # ── 2. Assumptions ──

    with st.expander("⚙️ Assumptions (auto-generated — click to edit)", expanded=False):
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            rev_growth = st.number_input("Revenue Growth % MoM", value=suggested.revenue.growth_rate_pct or 0.0, step=0.5, format="%.1f")
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

    model = run_model(ingested, assumptions)
    analysis = model.analysis

    # ── 3. Analysis ──

    st.markdown("---")

    # Key metrics
    mc = st.columns(6)
    if analysis.ltm:
        l = analysis.ltm
        with mc[0]: st.metric("LTM Revenue", f"${l.ltm_revenue/1e6:.1f}M" if l.ltm_revenue else "—")
        with mc[1]: st.metric("LTM EBITDA", f"${l.ltm_ebitda/1e6:.1f}M" if l.ltm_ebitda else "—")
        with mc[2]: st.metric("EBITDA Margin", f"{l.ltm_ebitda_margin_pct:.1f}%" if l.ltm_ebitda_margin_pct else "—")
        with mc[3]: st.metric("Rule of 40", f"{l.rule_of_40:.0f}" if l.rule_of_40 else "—")
    if model.returns and model.returns.moic:
        with mc[4]: st.metric("MOIC", f"{model.returns.moic:.2f}x")
        with mc[5]: st.metric("IRR", f"{model.returns.irr:.0%}" if model.returns.irr else "—")

    # Excel download — use original ingested quality scores, combined data for content
    buf = io.BytesIO()
    # Copy quality scores from original ingested data to combined data for Excel
    export_data = {}
    for doc_type, nr in model.combined_data.items():
        export_nr = NormalizedResult(
            df=nr.df,
            doc_type=nr.doc_type,
            doc_type_name=nr.doc_type_name,
            company_name=nr.company_name,
            quality_score=ingested[doc_type].quality_score if doc_type in ingested else nr.quality_score,
        )
        export_data[doc_type] = export_nr
    export_to_excel(analysis, buf, ingested=export_data, company_name=company)
    excel_bytes = buf.getvalue()

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("📥 Download Excel", excel_bytes, file_name=f"{company}_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with dl2:
        # Generate PPTX
        from exports.pptx_export import export_to_pptx
        pptx_buf = io.BytesIO()
        export_to_pptx(
            analysis=analysis,
            research_brief=st.session_state.get("research"),
            value_creation=st.session_state.get("vc_plan"),
            model_result=model,
            company_name=company,
            sector=sector,
            filepath=pptx_buf,
        )
        st.download_button("📥 Download Presentation", pptx_buf.getvalue(),
                           file_name=f"{company}_{date.today()}.pptx",
                           mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                           use_container_width=True)

    # Tabs
    tab_names = []
    if analysis.ebitda_bridges: tab_names.append("EBITDA Bridge")
    if analysis.margins: tab_names.append("Margins")
    if analysis.variance: tab_names.append("Variance")
    if analysis.working_capital: tab_names.append("Working Capital")
    if analysis.fcf: tab_names.append("FCF")
    if analysis.ltm: tab_names.append("LTM & Rule of 40")
    if analysis.revenue_analytics: tab_names.append("Revenue")
    if analysis.trends: tab_names.append("Flags")
    tab_names.append("Forecast")

    tabs = st.tabs(tab_names)
    ti = 0

    if analysis.ebitda_bridges:
        with tabs[ti]:
            eb = analysis.ebitda_bridges
            cols = st.columns(3 if eb.vs_prior_year else (2 if eb.vs_budget else 1))
            def _bridge(b, col):
                if not b: return
                with col:
                    st.markdown(f"**{b.label}** ({b.base_period} → {b.current_period})")
                    st.write(f"Starting: **{_fmt(b.base_ebitda)}**")
                    for c in b.components:
                        clr = "green" if c.value >= 0 else "red"
                        st.markdown(f":{clr}[{c.name}: {_fmt_signed(c.value)}]")
                    st.write(f"Ending: **{_fmt(b.current_ebitda)}** (Δ {_fmt_signed(b.total_change)})")
                    st.caption("✅ Verified" if b.is_verified else "⚠️ Check")
            _bridge(eb.mom, cols[0])
            if eb.vs_budget and len(cols) > 1: _bridge(eb.vs_budget, cols[1])
            if eb.vs_prior_year and len(cols) > 2: _bridge(eb.vs_prior_year, cols[2])
        ti += 1

    if analysis.margins:
        with tabs[ti]:
            if not analysis.margins.as_dataframe.empty:
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
                rows_data = [{"": "🟢" if v.favorable == Favorability.FAVORABLE else ("🔴" if v.favorable == Favorability.UNFAVORABLE else "⚪"), "Line": v.line_item.replace("_"," ").title(), "Actual": f"${v.actual:,.0f}", "Prior": f"${v.comparator:,.0f}", "Change": f"${v.dollar_change:+,.0f}", "%": f"{v.pct_change:+.1f}%" if v.pct_change else ""} for v in data]
                st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.working_capital:
        with tabs[ti]:
            wc_rows = [{"Period": p.period, "DSO": f"{p.dso:.0f}" if p.dso else "", "DPO": f"{p.dpo:.0f}" if p.dpo else "", "CCC": f"{p.ccc:.0f}" if p.ccc else "", "WC Change": f"${p.wc_change:+,.0f}" if p.wc_change is not None else ""} for p in analysis.working_capital.periods]
            st.dataframe(pd.DataFrame(wc_rows), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.fcf:
        with tabs[ti]:
            fcf_rows = [{"Period": p.period, "FCF": f"${p.free_cash_flow:,.0f}" if p.free_cash_flow else "", "Cash Conv": f"{p.cash_conversion_ratio:.0%}" if p.cash_conversion_ratio else "", "ND/EBITDA": f"{p.net_debt_to_ltm_ebitda:.1f}x" if p.net_debt_to_ltm_ebitda else ""} for p in analysis.fcf.periods]
            st.dataframe(pd.DataFrame(fcf_rows), use_container_width=True, hide_index=True)
        ti += 1

    if analysis.ltm:
        with tabs[ti]:
            l = analysis.ltm
            lc1, lc2, lc3, lc4 = st.columns(4)
            with lc1: st.metric("LTM Revenue", _fmt(l.ltm_revenue) if l.ltm_revenue else "—")
            with lc2: st.metric("LTM EBITDA", _fmt(l.ltm_ebitda) if l.ltm_ebitda else "—")
            with lc3: st.metric("EBITDA Margin", f"{l.ltm_ebitda_margin_pct:.1f}%" if l.ltm_ebitda_margin_pct else "—")
            with lc4: st.metric("Rule of 40", f"{l.rule_of_40:.0f}" if l.rule_of_40 else "—")
            st.caption(f"{l.months_included} months · as of {l.as_of_period}")
            if l.rule_of_40 is not None:
                if l.rule_of_40 >= 40:
                    st.success(f"Growth {l.ltm_revenue_growth_yoy:.1f}% + Margin {l.ltm_ebitda_margin_pct:.1f}% = {l.rule_of_40:.1f}")
                else:
                    st.warning(f"Below threshold by {40 - l.rule_of_40:.1f} points")
        ti += 1

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

    if analysis.trends:
        with tabs[ti]:
            flags = analysis.trends.flags
            if not flags:
                st.success("No flags — all metrics normal.")
            else:
                for f in sorted(flags, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity.value, 3)):
                    icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(f.severity.value, "⚪")
                    st.markdown(f"{icon} **{f.metric.replace('_',' ').title()}** — {f.detail}")
        ti += 1

    with tabs[ti]:
        if "income_statement" in model.combined_data:
            df = model.combined_data["income_statement"].df.copy()
            pcol = "period" if "period" in df.columns else "month"
            df["Type"] = df["_is_projected"].apply(lambda x: "📈 Projected" if x else "📊 Actual")
            display = df[[pcol, "Type", "revenue", "cogs", "gross_profit", "ebitda"]].copy()
            for c in ["revenue", "cogs", "gross_profit", "ebitda"]:
                display[c] = display[c].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
            st.dataframe(display, use_container_width=True, hide_index=True, height=400)

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. MARKET RESEARCH
    # ═══════════════════════════════════════════════════════════════════════

    st.markdown("### Market Research")
    st.caption("Deep competitive intelligence — peer financials, market positioning, sector-specific trends.")

    if st.button("🔍 Run Research", use_container_width=True):
        with st.spinner("Researching competitors, market trends, and sector data..."):
            try:
                from research.engine import run_research
                company_metrics = {}
                if analysis.margins and analysis.margins.periods:
                    m = analysis.margins.periods[-1]
                    company_metrics = {k: getattr(m, k) for k in ["gross_margin_pct", "ebitda_margin_pct", "revenue_growth_yoy", "sm_pct_revenue", "rd_pct_revenue", "ga_pct_revenue"] if getattr(m, k, None) is not None}
                    # Fix key name
                    if "revenue_growth_yoy" in company_metrics:
                        company_metrics["revenue_growth_yoy_pct"] = company_metrics.pop("revenue_growth_yoy")
                if analysis.ltm:
                    company_metrics["ltm_revenue"] = analysis.ltm.ltm_revenue
                    company_metrics["ltm_ebitda"] = analysis.ltm.ltm_ebitda
                brief = run_research(company, sector, company_metrics)
                st.session_state["research"] = brief
            except Exception as e:
                st.error(f"Research failed: {e}")

    if "research" in st.session_state:
        import re
        brief = st.session_state["research"]

        # ── Peer Comparison Table ──
        if brief.peer_companies:
            st.subheader("Peer Benchmarking")
            peer_rows = []
            if analysis.margins and analysis.margins.periods:
                m = analysis.margins.periods[-1]
                ltm_rev = analysis.ltm.ltm_revenue if analysis.ltm else None
                peer_rows.append({
                    "Company": f"{company} ★",
                    "Revenue": f"${ltm_rev/1e6:.0f}M" if ltm_rev else "—",
                    "Gross Margin": f"{m.gross_margin_pct:.1f}%" if m.gross_margin_pct else "—",
                    "EBITDA Margin": f"{m.ebitda_margin_pct:.1f}%" if m.ebitda_margin_pct else "—",
                    "Growth YoY": f"{m.revenue_growth_yoy:+.1f}%" if m.revenue_growth_yoy else "—",
                    "EV/EBITDA": "—",
                })
            for p in brief.peer_companies:
                rev = f"${p.revenue/1e9:.1f}B" if p.revenue and p.revenue > 1e9 else (f"${p.revenue/1e6:.0f}M" if p.revenue else "—")
                peer_rows.append({
                    "Company": f"{p.name} ({p.ticker})",
                    "Revenue": rev,
                    "Gross Margin": f"{p.gross_margin_pct:.1f}%" if p.gross_margin_pct else "—",
                    "EBITDA Margin": f"{p.ebitda_margin_pct:.1f}%" if p.ebitda_margin_pct else "—",
                    "Growth YoY": f"{p.revenue_growth_yoy_pct:.1f}%" if p.revenue_growth_yoy_pct else "—",
                    "EV/EBITDA": f"{p.ev_to_ebitda:.1f}x" if p.ev_to_ebitda else "—",
                })
            st.dataframe(pd.DataFrame(peer_rows), use_container_width=True, hide_index=True)

        # ── Gap Analysis ──
        if brief.gaps:
            st.subheader("Gap Analysis")
            gap_rows = []
            for g in brief.gaps:
                status = "🟢 Strength" if g.gap > 2 else ("🔴 Gap" if g.gap < -2 else "⚪ In Line")
                gap_rows.append({
                    "Metric": g.metric,
                    "Company": f"{g.company_value:.1f}%",
                    "Peer Median": f"{g.peer_median:.1f}%",
                    "Delta": f"{g.gap:+.1f}pp",
                    "Status": status,
                })
            st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)

        # ── Sector Intelligence (clean, concise) ──
        if brief.industry_context:
            st.subheader("Sector Intelligence")
            # Clean: remove citations, grok tags, excessive formatting
            clean = brief.industry_context
            clean = re.sub(r'\[\d+\]', '', clean)
            clean = re.sub(r'<[^>]+>', '', clean)
            clean = re.sub(r'\n{3,}', '\n\n', clean)
            # Take first ~1500 chars for readability
            if len(clean) > 1500:
                # Cut at last sentence boundary
                cut = clean[:1500].rfind('.')
                if cut > 500:
                    clean = clean[:cut + 1]
            st.markdown(clean)

        # ── Strategic Summary ──
        if brief.synthesis:
            st.subheader("Strategic Summary")
            # Clean synthesis too
            synth = brief.synthesis
            synth = re.sub(r'\[\d+\]', '', synth)
            synth = re.sub(r'<[^>]+>', '', synth)
            # Remove broken LaTeX/math artifacts
            synth = re.sub(r'\$[^$]+\$', '', synth)
            st.markdown(synth[:2000])

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. VALUE CREATION
    # ═══════════════════════════════════════════════════════════════════════

    st.markdown("### Value Creation Analysis")
    st.caption("AI agents analyze financial data + market research to find specific, dollar-sized opportunities.")

    if st.button("🤖 Run AI Value Creation Analysis", use_container_width=True):
        with st.spinner("Running 3 specialist AI agents + synthesis (financial analysis, AI tool research, strategic positioning)..."):
            try:
                from value_creation.engine import run_value_creation
                research = st.session_state.get("research")
                vc_plan = run_value_creation(company, sector, analysis, research)
                st.session_state["vc_plan"] = vc_plan
            except Exception as e:
                st.error(f"Value creation analysis failed: {e}")

    if "vc_plan" in st.session_state:
        vc = st.session_state["vc_plan"]

        # Show any agent errors for debugging
        if hasattr(vc, '_errors') and vc._errors:
            with st.expander(f"⚠️ Agent issues ({len(vc._errors)})"):
                for err in vc._errors:
                    st.warning(err)

        # Executive Summary
        if vc.executive_summary:
            st.subheader("Executive Summary")
            st.markdown(vc.executive_summary)

        # Total opportunity
        if vc.total_ebitda_opportunity > 0:
            st.metric("Total Annual EBITDA Opportunity", _fmt(vc.total_ebitda_opportunity))

        # Prioritized Plan
        if vc.prioritized_plan:
            st.subheader("Prioritized Initiatives")
            plan_rows = []
            for i, init in enumerate(vc.prioritized_plan, 1):
                plan_rows.append({
                    "#": i,
                    "Initiative": init.name,
                    "Category": init.category,
                    "Annual Impact": _fmt(init.ebitda_impact_annual),
                    "Cost": _fmt(init.implementation_cost),
                    "Timeline": f"{init.timeline_months}mo",
                    "Confidence": init.confidence,
                    "Tools": ", ".join(init.specific_tools) if init.specific_tools else "—",
                })
            st.dataframe(pd.DataFrame(plan_rows), use_container_width=True, hide_index=True)

        # AI Transformation
        if vc.ai_automation_opportunities or vc.ai_product_recommendations or vc.ai_disruption_risks:
            st.subheader("AI Transformation Roadmap")

            if vc.ai_automation_opportunities:
                with st.expander(f"🔧 AI Automation ({len(vc.ai_automation_opportunities)} opportunities)", expanded=True):
                    for a in vc.ai_automation_opportunities:
                        tools = ", ".join(a.specific_tools) if a.specific_tools else ""
                        st.markdown(f"**{a.name}** {f'({tools})' if tools else ''}")
                        st.caption(a.description)

            if vc.ai_product_recommendations:
                with st.expander(f"🚀 Product AI Features ({len(vc.ai_product_recommendations)})"):
                    for r in vc.ai_product_recommendations:
                        st.markdown(f"• {r}")

            if vc.ai_disruption_risks:
                with st.expander(f"⚠️ AI Disruption Risks ({len(vc.ai_disruption_risks)})"):
                    for r in vc.ai_disruption_risks:
                        st.markdown(f"• {r}")

            if vc.proprietary_ai_opportunities:
                with st.expander(f"🏗️ Build Proprietary AI ({len(vc.proprietary_ai_opportunities)})"):
                    for r in vc.proprietary_ai_opportunities:
                        st.markdown(f"• {r}")

        # Strategic
        if vc.strategic_priorities:
            st.subheader("Strategic Priorities")
            for p in vc.strategic_priorities:
                st.markdown(f"• {p}")

        if vc.key_risks:
            st.subheader("Key Risks")
            for r in vc.key_risks:
                st.markdown(f"• {r}")

        if vc.exit_readiness_notes:
            with st.expander("Exit Readiness Assessment"):
                st.markdown(vc.exit_readiness_notes)

        if vc.conflicts_resolved:
            with st.expander("Agent Conflicts Resolved"):
                for c in vc.conflicts_resolved:
                    st.caption(c)

else:
    st.markdown("---")
    st.caption("Select a company and click **Run Analysis** to get started.")
