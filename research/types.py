"""
Result dataclasses for the research module.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyProfile:
    """Claude-generated understanding of what the company actually is."""
    business_description: str = ""
    sub_sector: str = ""
    revenue_bracket: str = ""
    target_market: str = ""
    business_model: str = ""
    suggested_comps: list[dict] = field(default_factory=list)  # [{ticker, name, reason}]
    research_queries: list[str] = field(default_factory=list)
    key_competitive_factors: list[str] = field(default_factory=list)


@dataclass
class PeerCompany:
    """Financial data for one public comparable company."""
    name: str
    ticker: str
    revenue: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    revenue_growth_yoy_pct: Optional[float] = None
    market_cap: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    source: str = ""


@dataclass
class IndustryBenchmark:
    """Benchmark range for one metric in one sector."""
    sector: str
    metric: str
    percentile_25: float
    median: float
    percentile_75: float
    source: str = ""


@dataclass
class GapAnalysis:
    """One metric gap between the company and peer median."""
    metric: str
    company_value: float
    peer_median: float
    gap: float
    percentile_rank: str  # "above median", "below 25th", etc.
    opportunity: str      # human-readable description


@dataclass
class MacroContext:
    """Current macroeconomic environment."""
    fed_funds_rate: Optional[float] = None
    treasury_10y: Optional[float] = None
    sp500_level: Optional[float] = None
    sp500_ytd_pct: Optional[float] = None
    sector_etf_ytd_pct: Optional[float] = None
    as_of_date: str = ""


@dataclass
class NewsItem:
    """One news item about the company, competitor, or industry."""
    title: str
    source: str = ""
    date: str = ""
    snippet: str = ""
    relevance: str = "industry"  # "company" | "competitor" | "industry"
    url: str = ""


@dataclass
class ResearchBrief:
    """Complete external research package for one portfolio company."""
    company_name: str
    sector: str
    profile: CompanyProfile = field(default_factory=CompanyProfile)
    peer_companies: list[PeerCompany] = field(default_factory=list)
    benchmarks: list[IndustryBenchmark] = field(default_factory=list)
    gaps: list[GapAnalysis] = field(default_factory=list)
    macro: MacroContext = field(default_factory=MacroContext)
    news: list[NewsItem] = field(default_factory=list)
    industry_context: str = ""
    synthesis: str = ""
    generated_at: str = ""
