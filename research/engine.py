"""
Research engine orchestrator.

Gathers external data from all sources and produces a complete ResearchBrief.
"""

from datetime import date

from research.types import ResearchBrief, MacroContext
from research.benchmarks import get_benchmarks
from research.peers import get_peer_financials, suggest_peers
from research.macro import get_macro_context
from research.perplexity import research_industry, get_recent_news
from research.synthesize import compute_gaps, generate_synthesis


def run_research(
    company_name: str,
    sector: str,
    company_metrics: dict,
    peer_tickers: list[str] | None = None,
) -> ResearchBrief:
    """
    Run the full external research pipeline.

    company_metrics should include keys like:
        gross_margin_pct, ebitda_margin_pct, revenue_growth_yoy_pct,
        sm_pct_revenue, rd_pct_revenue, ga_pct_revenue, etc.
    """
    brief = ResearchBrief(
        company_name=company_name,
        sector=sector,
        generated_at=date.today().isoformat(),
    )

    # 1. Industry benchmarks (instant, no API call)
    brief.benchmarks = get_benchmarks(sector)

    # 2. Peer financials (yfinance)
    if peer_tickers is None:
        peer_tickers = suggest_peers(sector)
    brief.peer_companies = get_peer_financials(peer_tickers)

    # 3. Macro context (yfinance)
    try:
        brief.macro = get_macro_context(sector)
    except Exception:
        brief.macro = MacroContext(as_of_date=date.today().isoformat())

    # 4. Industry context (Perplexity)
    try:
        brief.industry_context = research_industry(company_name, sector)
    except Exception:
        brief.industry_context = ""

    # 5. Recent news (Perplexity)
    try:
        brief.news = get_recent_news(company_name, sector)
    except Exception:
        brief.news = []

    # 6. Gap analysis (pure math)
    brief.gaps = compute_gaps(company_metrics, brief.peer_companies, brief.benchmarks)

    # 7. Claude synthesis
    try:
        news_summaries = [f"{n.title}: {n.snippet[:100]}" for n in brief.news if n.title]
        brief.synthesis = generate_synthesis(
            company_name, sector, company_metrics,
            brief.gaps, brief.industry_context, news_summaries,
        )
    except Exception:
        brief.synthesis = ""

    return brief
