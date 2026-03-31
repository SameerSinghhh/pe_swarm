"""
Tool definitions and executor for the conversational AI agent.

Each tool calls a REAL function from our analysis/modeling/research engine.
The agent NEVER does math itself — it always calls a verified tool.
"""

import json
from analysis.types import AnalysisResult, Favorability
from research.types import ResearchBrief
from modeling.types import AssumptionSet, ModelResult
from value_creation.context import build_context_block


# ── Tool Definitions (for Claude API) ──

TOOL_DEFINITIONS = [
    {
        "name": "get_current_metrics",
        "description": "Get the latest financial metrics: LTM revenue, EBITDA, margins, growth rates, Rule of 40, cost structure percentages. Use this for any question about the company's current financial performance.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_ebitda_bridge",
        "description": "Get the EBITDA bridge showing exactly what drove the change in EBITDA. Shows revenue impact, COGS, S&M, R&D, G&A components. Use for questions about what drove EBITDA up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bridge_type": {
                    "type": "string",
                    "enum": ["mom", "budget", "prior_year"],
                    "description": "Which bridge: mom (month over month), budget (actual vs budget), or prior_year",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_variance_analysis",
        "description": "Get detailed variance analysis for every P&L line item. Shows actual vs comparator, dollar change, percentage change, and whether favorable or unfavorable.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_working_capital",
        "description": "Get working capital metrics: DSO (days sales outstanding), DPO (days payable outstanding), cash conversion cycle, working capital changes, and AR aging.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_trend_flags",
        "description": "Get all automatically detected anomalies, declining trends, margin compression, and threshold crossings across all metrics.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "run_scenario",
        "description": "Model a what-if scenario by changing assumptions. Returns the projected impact on EBITDA, revenue, margins, and returns (MOIC/IRR). Use this whenever the user asks 'what if we...' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "revenue_growth_pct": {"type": "number", "description": "Monthly revenue growth rate %"},
                "cogs_pct": {"type": "number", "description": "COGS as % of revenue"},
                "sm_pct": {"type": "number", "description": "S&M as % of revenue"},
                "rd_pct": {"type": "number", "description": "R&D as % of revenue"},
                "ga_pct": {"type": "number", "description": "G&A as % of revenue"},
                "dso_target": {"type": "number", "description": "Target DSO in days"},
                "exit_multiple": {"type": "number", "description": "Exit EV/EBITDA multiple"},
            },
            "required": [],
        },
    },
    {
        "name": "search_market",
        "description": "Search the internet for specific information using Perplexity. Use for questions about competitors, AI tools, industry trends, pricing data, or any external information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_peer_comparison",
        "description": "Get peer comparison data: comparable public companies with their revenue, margins, growth, and valuation multiples, plus gap analysis showing where this company is above/below peers.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ── Tool Executor ──

def execute_tool(
    tool_name: str,
    tool_input: dict,
    context: dict,
) -> str:
    """
    Execute a tool and return the result as a string.

    context contains:
        - analysis: AnalysisResult
        - ingested: dict[str, NormalizedResult]
        - assumptions: AssumptionSet
        - model: ModelResult
        - research: ResearchBrief or None
        - company_name: str
        - sector: str
    """
    try:
        if tool_name == "get_current_metrics":
            return _get_current_metrics(context)
        elif tool_name == "get_ebitda_bridge":
            return _get_ebitda_bridge(context, tool_input.get("bridge_type", "mom"))
        elif tool_name == "get_variance_analysis":
            return _get_variance(context)
        elif tool_name == "get_working_capital":
            return _get_working_capital(context)
        elif tool_name == "get_trend_flags":
            return _get_trend_flags(context)
        elif tool_name == "run_scenario":
            return _run_scenario(context, tool_input)
        elif tool_name == "search_market":
            return _search_market(tool_input.get("query", ""))
        elif tool_name == "get_peer_comparison":
            return _get_peer_comparison(context)
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool error: {e}"


def _get_current_metrics(ctx) -> str:
    analysis = ctx.get("analysis")
    if not analysis:
        return "No analysis data available. Please run analysis first."

    lines = []

    if analysis.ltm:
        l = analysis.ltm
        if l.ltm_revenue: lines.append(f"LTM Revenue: ${l.ltm_revenue:,.0f}")
        if l.ltm_ebitda: lines.append(f"LTM EBITDA: ${l.ltm_ebitda:,.0f}")
        if l.ltm_gross_margin_pct: lines.append(f"LTM Gross Margin: {l.ltm_gross_margin_pct:.1f}%")
        if l.ltm_ebitda_margin_pct: lines.append(f"LTM EBITDA Margin: {l.ltm_ebitda_margin_pct:.1f}%")
        if l.ltm_revenue_growth_yoy: lines.append(f"LTM Revenue Growth YoY: {l.ltm_revenue_growth_yoy:.1f}%")
        if l.rule_of_40: lines.append(f"Rule of 40: {l.rule_of_40:.1f}")

    if analysis.margins and analysis.margins.periods:
        m = analysis.margins.periods[-1]
        lines.append(f"\nLatest Period ({m.period}):")
        if m.gross_margin_pct: lines.append(f"  Gross Margin: {m.gross_margin_pct:.1f}%")
        if m.ebitda_margin_pct: lines.append(f"  EBITDA Margin: {m.ebitda_margin_pct:.1f}%")
        if m.sm_pct_revenue: lines.append(f"  S&M: {m.sm_pct_revenue:.1f}% of revenue")
        if m.rd_pct_revenue: lines.append(f"  R&D: {m.rd_pct_revenue:.1f}% of revenue")
        if m.ga_pct_revenue: lines.append(f"  G&A: {m.ga_pct_revenue:.1f}% of revenue")
        if m.revenue_growth_mom: lines.append(f"  Revenue Growth MoM: {m.revenue_growth_mom:.1f}%")
        if m.revenue_growth_yoy: lines.append(f"  Revenue Growth YoY: {m.revenue_growth_yoy:.1f}%")

    model = ctx.get("model")
    if model and model.returns:
        r = model.returns
        if r.moic: lines.append(f"\nReturns: MOIC {r.moic:.2f}x, IRR {r.irr:.0%}" if r.irr else "")

    return "\n".join(lines) if lines else "No metrics available."


def _get_ebitda_bridge(ctx, bridge_type) -> str:
    analysis = ctx.get("analysis")
    if not analysis or not analysis.ebitda_bridges:
        return "No EBITDA bridge data available."

    eb = analysis.ebitda_bridges
    b = None
    if bridge_type == "mom": b = eb.mom
    elif bridge_type == "budget": b = eb.vs_budget
    elif bridge_type == "prior_year": b = eb.vs_prior_year

    if not b:
        return f"No {bridge_type} bridge available."

    lines = [f"EBITDA Bridge ({b.label}: {b.base_period} → {b.current_period})"]
    lines.append(f"Starting EBITDA: ${b.base_ebitda:,.0f}")
    for c in b.components:
        lines.append(f"  {c.name}: ${c.value:+,.0f}")
    lines.append(f"Ending EBITDA: ${b.current_ebitda:,.0f}")
    lines.append(f"Total Change: ${b.total_change:+,.0f}")
    lines.append(f"Verified: {'Yes' if b.is_verified else 'No'}")
    return "\n".join(lines)


def _get_variance(ctx) -> str:
    analysis = ctx.get("analysis")
    if not analysis or not analysis.variance:
        return "No variance data available."

    latest = analysis.variance.periods[-1]
    data = latest.vs_prior_month
    if not data:
        return "No prior month variance data."

    lines = [f"Variance Analysis — {latest.period} vs Prior Month"]
    for v in data:
        fav = "Favorable" if v.favorable == Favorability.FAVORABLE else ("Unfavorable" if v.favorable == Favorability.UNFAVORABLE else "Neutral")
        lines.append(f"  {v.line_item.replace('_',' ').title()}: ${v.actual:,.0f} vs ${v.comparator:,.0f} = ${v.dollar_change:+,.0f} ({v.pct_change:+.1f}% — {fav})" if v.pct_change else f"  {v.line_item}: ${v.dollar_change:+,.0f}")
    return "\n".join(lines)


def _get_working_capital(ctx) -> str:
    analysis = ctx.get("analysis")
    if not analysis or not analysis.working_capital:
        return "No working capital data available."

    lines = ["Working Capital Metrics:"]
    for p in analysis.working_capital.periods[-3:]:
        parts = [f"  {p.period}:"]
        if p.dso: parts.append(f"DSO={p.dso:.0f}")
        if p.dpo: parts.append(f"DPO={p.dpo:.0f}")
        if p.ccc: parts.append(f"CCC={p.ccc:.0f}")
        if p.wc_change is not None: parts.append(f"WC Change=${p.wc_change:+,.0f}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _get_trend_flags(ctx) -> str:
    analysis = ctx.get("analysis")
    if not analysis or not analysis.trends:
        return "No trend flags detected."

    flags = analysis.trends.flags
    if not flags:
        return "No trend flags — all metrics within normal range."

    lines = [f"Detected {len(flags)} trend flags:"]
    for f in sorted(flags, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x.severity.value, 3)):
        lines.append(f"  [{f.severity.value.upper()}] {f.metric}: {f.detail}")
    return "\n".join(lines)


def _run_scenario(ctx, params) -> str:
    """Run a what-if scenario by modifying assumptions and re-running the model."""
    from modeling.types import (
        AssumptionSet, RevenueAssumptions, CostAssumptions, CostLineAssumption,
        WorkingCapitalAssumptions, ExitAssumptions,
    )
    from modeling.engine import run_model

    ingested = ctx.get("ingested", {})
    base = ctx.get("assumptions")
    if not ingested or not base:
        return "No data loaded to run scenario."

    # Build modified assumptions
    rev_growth = params.get("revenue_growth_pct", base.revenue.growth_rate_pct or 0)
    cogs = params.get("cogs_pct")
    sm = params.get("sm_pct")
    rd = params.get("rd_pct")
    ga = params.get("ga_pct")
    dso = params.get("dso_target", base.working_capital.target_dso)
    exit_m = params.get("exit_multiple", base.exit_.exit_multiple)

    # Use base values for anything not specified
    def _get_base_pct(item):
        for cl in base.costs.lines:
            if cl.line_item == item:
                return cl.pct_of_revenue or 0
        return 0

    new_assumptions = AssumptionSet(
        projection_months=base.projection_months,
        revenue=RevenueAssumptions(method="growth_rate", growth_rate_pct=rev_growth),
        costs=CostAssumptions(lines=[
            CostLineAssumption("cogs", method="pct_of_revenue", pct_of_revenue=cogs or _get_base_pct("cogs")),
            CostLineAssumption("sales_marketing", method="pct_of_revenue", pct_of_revenue=sm or _get_base_pct("sales_marketing")),
            CostLineAssumption("rd", method="pct_of_revenue", pct_of_revenue=rd or _get_base_pct("rd")),
            CostLineAssumption("ga", method="pct_of_revenue", pct_of_revenue=ga or _get_base_pct("ga")),
        ]),
        working_capital=WorkingCapitalAssumptions(target_dso=dso, target_dpo=base.working_capital.target_dpo),
        capex=base.capex, debt=base.debt, tax=base.tax,
        exit_=ExitAssumptions(exit_year=base.exit_.exit_year, exit_multiple=exit_m, entry_equity=base.exit_.entry_equity),
    )

    try:
        result = run_model(ingested, new_assumptions)
        lines = ["Scenario Results:"]

        if result.analysis.ltm:
            l = result.analysis.ltm
            lines.append(f"  Projected LTM Revenue: ${l.ltm_revenue:,.0f}")
            lines.append(f"  Projected LTM EBITDA: ${l.ltm_ebitda:,.0f}")
            lines.append(f"  EBITDA Margin: {l.ltm_ebitda_margin_pct:.1f}%")
            if l.rule_of_40: lines.append(f"  Rule of 40: {l.rule_of_40:.1f}")

        if result.returns:
            r = result.returns
            if r.moic: lines.append(f"  MOIC: {r.moic:.2f}x")
            if r.irr: lines.append(f"  IRR: {r.irr:.0%}")
            if r.exit_equity: lines.append(f"  Exit Equity: ${r.exit_equity:,.0f}")

        # Compare to base
        base_model = ctx.get("model")
        if base_model and base_model.analysis.ltm and result.analysis.ltm:
            base_ebitda = base_model.analysis.ltm.ltm_ebitda or 0
            new_ebitda = result.analysis.ltm.ltm_ebitda or 0
            delta = new_ebitda - base_ebitda
            lines.append(f"\n  vs Base Case: EBITDA ${delta:+,.0f} ({'+' if delta >= 0 else ''}{delta/base_ebitda*100:.1f}%)" if base_ebitda else "")

        return "\n".join(lines)
    except Exception as e:
        return f"Scenario failed: {e}"


def _search_market(query) -> str:
    """Search the web using Perplexity."""
    from research.perplexity import ai_search
    result = ai_search(query)
    if result:
        # Clean up
        import re
        clean = re.sub(r'\[\d+\]', '', result)
        clean = re.sub(r'<[^>]+>', '', clean)
        return clean[:2000]
    return "No results found."


def _get_peer_comparison(ctx) -> str:
    research = ctx.get("research")
    if not research:
        # Run research on the fly
        from research.engine import run_research
        analysis = ctx.get("analysis")
        company_metrics = {}
        if analysis and analysis.margins and analysis.margins.periods:
            m = analysis.margins.periods[-1]
            company_metrics = {
                "gross_margin_pct": m.gross_margin_pct,
                "ebitda_margin_pct": m.ebitda_margin_pct,
            }
        if analysis and analysis.ltm:
            company_metrics["ltm_revenue"] = analysis.ltm.ltm_revenue

        try:
            research = run_research(ctx.get("company_name", ""), ctx.get("sector", ""), company_metrics)
        except Exception:
            return "Could not fetch peer data."

    lines = ["Peer Comparison:"]
    for p in research.peer_companies[:5]:
        lines.append(f"  {p.name} ({p.ticker}): Rev=${p.revenue/1e6:.0f}M, GM={p.gross_margin_pct}%, EBITDA={p.ebitda_margin_pct}%, Growth={p.revenue_growth_yoy_pct}%" if p.revenue else f"  {p.name} ({p.ticker})")

    if research.gaps:
        lines.append("\nGap Analysis:")
        for g in research.gaps:
            status = "STRENGTH" if g.gap > 2 else ("GAP" if g.gap < -2 else "IN LINE")
            lines.append(f"  {g.metric}: {g.company_value:.1f}% vs {g.peer_median:.1f}% ({g.gap:+.1f}pp) — {status}")

    return "\n".join(lines)
