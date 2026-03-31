"""
Claude synthesis: takes raw research data and produces gap analysis
and a strategic narrative.
"""

import json
import os
from dotenv import load_dotenv

from research.types import GapAnalysis, PeerCompany, IndustryBenchmark

load_dotenv()


def compute_gaps(
    company_metrics: dict,
    peers: list[PeerCompany],
    benchmarks: list[IndustryBenchmark],
) -> list[GapAnalysis]:
    """
    Compute gap analysis: where does the company sit vs peers and benchmarks?
    Pure math — no AI needed for this part.
    """
    gaps = []

    # Metrics to compare (company_key, benchmark_metric_name, display_name)
    comparisons = [
        ("gross_margin_pct", "gross_margin_pct", "Gross Margin"),
        ("ebitda_margin_pct", "ebitda_margin_pct", "EBITDA Margin"),
        ("revenue_growth_yoy_pct", "revenue_growth_yoy_pct", "Revenue Growth YoY"),
        ("sm_pct_revenue", "sm_pct_revenue", "S&M % of Revenue"),
        ("rd_pct_revenue", "rd_pct_revenue", "R&D % of Revenue"),
        ("ga_pct_revenue", "ga_pct_revenue", "G&A % of Revenue"),
    ]

    # Build peer median for each metric
    peer_medians = {}
    for metric_key in ["gross_margin_pct", "ebitda_margin_pct", "revenue_growth_yoy_pct"]:
        vals = [getattr(p, metric_key) for p in peers if getattr(p, metric_key) is not None]
        if vals:
            vals.sort()
            mid = len(vals) // 2
            peer_medians[metric_key] = vals[mid] if len(vals) % 2 == 1 else (vals[mid - 1] + vals[mid]) / 2

    # Build benchmark lookup
    bm_lookup = {b.metric: b for b in benchmarks}

    for company_key, bm_key, display in comparisons:
        company_val = company_metrics.get(company_key)
        if company_val is None:
            continue

        # Use peer median if available, else benchmark median
        median = peer_medians.get(bm_key)
        bm = bm_lookup.get(bm_key)

        if median is None and bm:
            median = bm.median

        if median is None:
            continue

        gap = company_val - median

        # Determine percentile rank
        if bm:
            if company_val >= bm.percentile_75:
                rank = "Top quartile"
            elif company_val >= bm.median:
                rank = "Above median"
            elif company_val >= bm.percentile_25:
                rank = "Below median"
            else:
                rank = "Bottom quartile"
        else:
            rank = "Above median" if gap >= 0 else "Below median"

        # Cost items: being BELOW median is good (lower costs)
        is_cost = "pct_revenue" in company_key and company_key not in ["gross_margin_pct", "ebitda_margin_pct"]

        if is_cost:
            opp = f"{display} is {abs(gap):.1f}pp {'above' if gap > 0 else 'below'} median ({median:.1f}%)"
            if gap > 0:
                opp += " — potential cost savings opportunity"
        else:
            direction = "above" if gap >= 0 else "below"
            opp = f"{display} is {abs(gap):.1f}pp {direction} median ({median:.1f}%)"
            if gap < 0:
                opp += " — improvement opportunity"

        gaps.append(GapAnalysis(
            metric=display,
            company_value=round(company_val, 1),
            peer_median=round(median, 1),
            gap=round(gap, 1),
            percentile_rank=rank,
            opportunity=opp,
        ))

    return gaps


def generate_synthesis(
    company_name: str,
    sector: str,
    company_metrics: dict,
    gaps: list[GapAnalysis],
    industry_context: str,
    news_summaries: list[str],
) -> str:
    """
    Use Claude to synthesize all research into a strategic narrative.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return ""

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return ""

    # Build the prompt
    gaps_text = "\n".join(f"- {g.opportunity}" for g in gaps) if gaps else "No gap data available."
    news_text = "\n".join(f"- {n}" for n in news_summaries[:5]) if news_summaries else "No recent news."
    metrics_text = "\n".join(f"- {k}: {v}" for k, v in company_metrics.items() if v is not None)

    prompt = f"""You are a PE operating partner writing a brief market context section for a portfolio company review.

COMPANY: {company_name}
SECTOR: {sector}

COMPANY METRICS:
{metrics_text}

GAP ANALYSIS VS PEERS:
{gaps_text}

INDUSTRY CONTEXT:
{industry_context or 'Not available.'}

RECENT NEWS:
{news_text}

Write 3-4 paragraphs covering:
1. How this company compares to peers (strengths and weaknesses based on the gaps)
2. Industry context and what it means for the company
3. Key risks and opportunities based on the data

Be direct and specific. Reference actual numbers. No hedging. Write as a PE analyst would for an investment committee memo."""

    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return ""
