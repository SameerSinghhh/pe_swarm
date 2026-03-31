"""
Research engine orchestrator.

Flow:
1. Claude builds a company profile (understands the business)
2. Targeted peer search using profile's suggested comps
3. Targeted industry research using profile's custom queries
4. Targeted news search for company + competitors
5. Gap analysis (pure math)
6. Claude synthesis with full context
"""

from datetime import date

from research.types import ResearchBrief, MacroContext
from research.company_profile import build_company_profile
from research.benchmarks import get_benchmarks
from research.peers import get_peer_financials
from research.macro import get_macro_context
from research.perplexity import research_with_queries, get_targeted_news
from research.synthesize import compute_gaps, generate_synthesis


def run_research(
    company_name: str,
    sector: str,
    company_metrics: dict,
    business_description: str = "",
    peer_tickers: list[str] | None = None,
) -> ResearchBrief:
    """
    Run the full intelligent research pipeline.

    Step 0: Claude understands the company
    Step 1-3: Targeted data gathering
    Step 4-5: Analysis and synthesis
    """
    brief = ResearchBrief(
        company_name=company_name,
        sector=sector,
        generated_at=date.today().isoformat(),
    )

    # ── Step 0: Build company profile (Claude) ──
    try:
        brief.profile = build_company_profile(
            company_name, sector, company_metrics, business_description,
        )
    except Exception:
        pass

    # ── Step 1: Peer financials (yfinance) ──
    # Use analyst-provided tickers if given, else use profile's suggestions
    if peer_tickers:
        tickers_to_pull = peer_tickers
    elif brief.profile.suggested_comps:
        tickers_to_pull = [c["ticker"] for c in brief.profile.suggested_comps]
    else:
        tickers_to_pull = []

    if tickers_to_pull:
        try:
            brief.peer_companies = get_peer_financials(tickers_to_pull)
        except Exception:
            pass

    # ── Step 2: Industry benchmarks (static, instant) ──
    # Use profile's sub_sector if available for more specific benchmarks
    bench_sector = brief.profile.sub_sector or sector
    brief.benchmarks = get_benchmarks(bench_sector)
    if not brief.benchmarks:
        brief.benchmarks = get_benchmarks(sector)

    # ── Step 3: Macro context (yfinance) ──
    try:
        brief.macro = get_macro_context(sector)
    except Exception:
        brief.macro = MacroContext(as_of_date=date.today().isoformat())

    # ── Step 4: Targeted industry research (Perplexity) ──
    if brief.profile.research_queries:
        try:
            brief.industry_context = research_with_queries(brief.profile.research_queries)
        except Exception:
            brief.industry_context = ""

    # ── Step 5: Targeted news (Perplexity) ──
    competitor_names = [c.get("name", "") for c in brief.profile.suggested_comps if c.get("name")]
    try:
        brief.news = get_targeted_news(
            company_name=company_name,
            competitor_names=competitor_names[:3],
            sub_sector=brief.profile.sub_sector or sector,
        )
    except Exception:
        pass

    # ── Step 6: Gap analysis (pure math) ──
    brief.gaps = compute_gaps(company_metrics, brief.peer_companies, brief.benchmarks)

    # ── Step 7: Claude synthesis ──
    try:
        news_summaries = [f"{n.title}: {n.snippet[:100]}" for n in brief.news if n.title]
        brief.synthesis = generate_synthesis(
            company_name=company_name,
            sector=brief.profile.sub_sector or sector,
            company_metrics=company_metrics,
            gaps=brief.gaps,
            industry_context=brief.industry_context,
            news_summaries=news_summaries,
        )
    except Exception:
        brief.synthesis = ""

    return brief
