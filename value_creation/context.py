"""
Context serializer. Converts AnalysisResult + ResearchBrief into
a compact text block that agents receive as context.
"""

from analysis.types import AnalysisResult
from research.types import ResearchBrief


def build_context_block(
    analysis: AnalysisResult,
    research_brief: ResearchBrief | None = None,
    company_name: str = "",
    sector: str = "",
) -> str:
    """Serialize all analysis + research into ~2500 tokens of context text."""
    sections = []

    # Company profile
    if research_brief and research_brief.profile:
        p = research_brief.profile
        if p.business_description:
            sections.append(f"COMPANY: {company_name}")
            sections.append(f"Sector: {sector}")
            sections.append(f"Description: {p.business_description}")
            if p.sub_sector: sections.append(f"Sub-sector: {p.sub_sector}")
            if p.revenue_bracket: sections.append(f"Revenue: {p.revenue_bracket}")
            if p.business_model: sections.append(f"Model: {p.business_model}")
            if p.target_market: sections.append(f"Market: {p.target_market}")

    # LTM metrics
    if analysis.ltm:
        l = analysis.ltm
        sections.append(f"\nLTM METRICS (as of {l.as_of_period}):")
        if l.ltm_revenue: sections.append(f"  LTM Revenue: ${l.ltm_revenue:,.0f}")
        if l.ltm_ebitda: sections.append(f"  LTM EBITDA: ${l.ltm_ebitda:,.0f}")
        if l.ltm_gross_margin_pct: sections.append(f"  Gross Margin: {l.ltm_gross_margin_pct:.1f}%")
        if l.ltm_ebitda_margin_pct: sections.append(f"  EBITDA Margin: {l.ltm_ebitda_margin_pct:.1f}%")
        if l.ltm_revenue_growth_yoy: sections.append(f"  Revenue Growth YoY: {l.ltm_revenue_growth_yoy:.1f}%")
        if l.rule_of_40: sections.append(f"  Rule of 40: {l.rule_of_40:.1f}")

    # Latest margins
    if analysis.margins and analysis.margins.periods:
        m = analysis.margins.periods[-1]
        sections.append(f"\nCOST STRUCTURE ({m.period}):")
        if m.sm_pct_revenue: sections.append(f"  S&M: {m.sm_pct_revenue:.1f}% of revenue")
        if m.rd_pct_revenue: sections.append(f"  R&D: {m.rd_pct_revenue:.1f}% of revenue")
        if m.ga_pct_revenue: sections.append(f"  G&A: {m.ga_pct_revenue:.1f}% of revenue")
        if m.opex_pct_revenue: sections.append(f"  Total OpEx: {m.opex_pct_revenue:.1f}% of revenue")

    # EBITDA bridge
    if analysis.ebitda_bridges and analysis.ebitda_bridges.mom:
        b = analysis.ebitda_bridges.mom
        sections.append(f"\nEBITDA BRIDGE (MoM: {b.base_period} → {b.current_period}):")
        sections.append(f"  Base EBITDA: ${b.base_ebitda:,.0f}")
        for c in b.components:
            sections.append(f"  {c.name}: ${c.value:+,.0f}")
        sections.append(f"  Current EBITDA: ${b.current_ebitda:,.0f}")

    # Working capital
    if analysis.working_capital and analysis.working_capital.periods:
        wc = analysis.working_capital.periods[-1]
        sections.append(f"\nWORKING CAPITAL ({wc.period}):")
        if wc.dso: sections.append(f"  DSO: {wc.dso:.0f} days")
        if wc.dpo: sections.append(f"  DPO: {wc.dpo:.0f} days")
        if wc.ccc: sections.append(f"  Cash Conversion Cycle: {wc.ccc:.0f} days")
        if wc.wc_change is not None: sections.append(f"  WC Change: ${wc.wc_change:+,.0f}")

    # FCF
    if analysis.fcf and analysis.fcf.periods:
        f = analysis.fcf.periods[-1]
        sections.append(f"\nFCF ({f.period}):")
        if f.free_cash_flow: sections.append(f"  Free Cash Flow: ${f.free_cash_flow:,.0f}")
        if f.cash_conversion_ratio: sections.append(f"  Cash Conversion: {f.cash_conversion_ratio:.0%}")
        if f.net_debt_to_ltm_ebitda: sections.append(f"  Net Debt / EBITDA: {f.net_debt_to_ltm_ebitda:.1f}x")

    # Revenue analytics
    if analysis.revenue_analytics:
        ra = analysis.revenue_analytics
        if ra.concentration:
            c = ra.concentration[-1]
            sections.append(f"\nREVENUE CONCENTRATION:")
            sections.append(f"  Top 1 {c.dimension}: {c.top1_pct:.1f}%")
            if c.top5_pct: sections.append(f"  Top 5: {c.top5_pct:.1f}%")
            sections.append(f"  HHI: {c.herfindahl:.3f}")

    # Trend flags
    if analysis.trends and analysis.trends.flags:
        sections.append(f"\nTREND FLAGS:")
        for flag in analysis.trends.flags[:8]:
            sections.append(f"  [{flag.severity.value}] {flag.metric}: {flag.detail}")

    # Peer benchmarks
    if research_brief and research_brief.peer_companies:
        sections.append(f"\nPEER COMPARISON:")
        for p in research_brief.peer_companies[:5]:
            sections.append(f"  {p.name} ({p.ticker}): GM={p.gross_margin_pct}%, EBITDA={p.ebitda_margin_pct}%, Growth={p.revenue_growth_yoy_pct}%")

    # Gap analysis
    if research_brief and research_brief.gaps:
        sections.append(f"\nGAP ANALYSIS:")
        for g in research_brief.gaps:
            sections.append(f"  {g.metric}: {g.company_value:.1f}% vs {g.peer_median:.1f}% median ({g.gap:+.1f}pp)")

    # Industry context (truncated)
    if research_brief and research_brief.industry_context:
        sections.append(f"\nINDUSTRY CONTEXT:")
        sections.append(f"  {research_brief.industry_context[:500]}")

    return "\n".join(sections)
