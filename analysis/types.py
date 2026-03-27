"""
All result dataclasses and enums for the analysis engine.

Every analysis module returns typed dataclasses — not raw dicts.
Every numeric result that involves division uses Optional[float]
to explicitly handle cases where the denominator is zero or missing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


# ── Enums ──

class Favorability(Enum):
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"
    NEUTRAL = "neutral"


class FlagType(Enum):
    CONSECUTIVE_DECLINE = "consecutive_decline"
    THRESHOLD_CROSSING = "threshold_crossing"
    ACCELERATION_CHANGE = "acceleration_change"
    MARGIN_COMPRESSION = "margin_compression"
    ANOMALY = "anomaly"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Module 1: EBITDA Bridge ──

@dataclass
class BridgeComponent:
    """One line in an EBITDA bridge waterfall."""
    name: str
    value: float


@dataclass
class EBITDABridge:
    """A single EBITDA bridge (MoM, vs Budget, or vs PY)."""
    label: str                          # "MoM", "vs Budget", "vs Prior Year"
    base_period: str                    # The comparator period label
    current_period: str
    base_ebitda: float
    current_ebitda: float
    components: list[BridgeComponent]   # The waterfall items
    total_change: float                 # current_ebitda - base_ebitda
    verification_delta: float           # abs(sum(components) - total_change) — must be ~0
    is_verified: bool                   # True if verification_delta < 0.01


@dataclass
class EBITDABridgeResult:
    """All bridges for a given period."""
    current_period: str
    mom: EBITDABridge | None = None
    vs_budget: EBITDABridge | None = None
    vs_prior_year: EBITDABridge | None = None


# ── Module 2: Variance Analysis ──

@dataclass
class LineVariance:
    """Variance for a single P&L line item against one comparator."""
    line_item: str
    actual: float
    comparator: float
    dollar_change: float
    pct_change: Optional[float]         # None if comparator is 0
    as_pct_of_revenue: Optional[float]  # None if revenue is 0
    favorable: Favorability


@dataclass
class PeriodVariance:
    """All variances for one period."""
    period: str
    vs_budget: list[LineVariance] | None = None
    vs_prior_month: list[LineVariance] | None = None
    vs_prior_year: list[LineVariance] | None = None


@dataclass
class VarianceResult:
    """Variance analysis across all periods."""
    periods: list[PeriodVariance]


# ── Module 3: Margins & Growth ──

@dataclass
class PeriodMargins:
    """All margin percentages and growth rates for one period."""
    period: str
    gross_margin_pct: Optional[float]
    ebitda_margin_pct: Optional[float]
    sm_pct_revenue: Optional[float]
    rd_pct_revenue: Optional[float]
    ga_pct_revenue: Optional[float]
    opex_pct_revenue: Optional[float]
    revenue_growth_mom: Optional[float]
    revenue_growth_yoy: Optional[float]
    ebitda_growth_mom: Optional[float]
    ebitda_growth_yoy: Optional[float]


@dataclass
class MarginsResult:
    """Margin and growth time series."""
    periods: list[PeriodMargins]
    as_dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)


# ── Module 4: Working Capital ──

@dataclass
class ARAgingPcts:
    """AR aging distribution percentages."""
    current_pct: Optional[float]
    pct_31_60: Optional[float]
    pct_61_90: Optional[float]
    pct_91_120: Optional[float]
    over_120_pct: Optional[float]


@dataclass
class PeriodWorkingCapital:
    """Working capital metrics for one period."""
    period: str
    dso: Optional[float]
    dpo: Optional[float]
    dio: Optional[float]
    ccc: Optional[float]               # DSO + DIO - DPO
    wc_change: Optional[float]          # Change in net working capital vs prior period
    dso_cash_impact: Optional[float]    # Cash freed/consumed by DSO change
    ar_aging: ARAgingPcts | None = None


@dataclass
class WorkingCapitalResult:
    """Working capital analysis across all periods."""
    periods: list[PeriodWorkingCapital]


# ── Module 5: FCF & Cash Conversion ──

@dataclass
class PeriodFCF:
    """FCF and leverage metrics for one period."""
    period: str
    free_cash_flow: Optional[float]
    cash_conversion_ratio: Optional[float]  # FCF / EBITDA
    net_debt: Optional[float]
    ltm_ebitda: Optional[float]
    net_debt_to_ltm_ebitda: Optional[float]


@dataclass
class FCFResult:
    """FCF analysis across all periods."""
    periods: list[PeriodFCF]


# ── Module 6: Revenue Analytics ──

@dataclass
class ConcentrationMetrics:
    """Revenue concentration for one period."""
    period: str
    dimension: str                      # "customer", "product", etc.
    top1_pct: Optional[float]
    top5_pct: Optional[float]
    top10_pct: Optional[float]
    herfindahl: Optional[float]         # 0-1, higher = more concentrated
    count: int                          # number of entities (customers, products)


@dataclass
class PriceVolumeDecomp:
    """Price/volume/mix decomposition for one period."""
    period: str
    price_effect: float
    volume_effect: float
    mix_effect: float
    total_change: float
    verification_delta: float           # abs(price + volume + mix - total_change)
    is_verified: bool


@dataclass
class RevenueAnalyticsResult:
    """All revenue analytics."""
    concentration: list[ConcentrationMetrics] = field(default_factory=list)
    price_volume: list[PriceVolumeDecomp] = field(default_factory=list)
    kpi_trends: dict = field(default_factory=dict)  # metric_name → list of (period, value)


# ── Module 7: Trend Detection ──

@dataclass
class TrendFlag:
    """One flagged trend or anomaly."""
    metric: str
    flag_type: FlagType
    severity: Severity
    current_value: float
    period: str
    detail: str


@dataclass
class TrendResult:
    """All detected trends and anomalies."""
    flags: list[TrendFlag]


# ── Top-level Result ──

@dataclass
class AnalysisResult:
    """Complete analysis output from the engine."""
    ebitda_bridges: EBITDABridgeResult | None = None
    variance: VarianceResult | None = None
    margins: MarginsResult | None = None
    working_capital: WorkingCapitalResult | None = None
    fcf: FCFResult | None = None
    revenue_analytics: RevenueAnalyticsResult | None = None
    trends: TrendResult | None = None
    modules_run: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
