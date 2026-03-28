"""
All assumption and result dataclasses for the modeling engine.

An AssumptionSet is a complete set of inputs for one scenario.
The analyst fills these in. The system does all the math.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from analysis.types import AnalysisResult, BridgeComponent


# ── Revenue ──

@dataclass
class RevenueAssumptions:
    """How to project future revenue."""
    method: str = "growth_rate"  # "growth_rate" | "target" | "saas_cohort"

    # Growth rate mode
    growth_rate_pct: Optional[float] = None  # MoM growth %
    growth_period: str = "mom"               # "mom" | "yoy"

    # Target mode: explicit amounts per period
    target_by_period: dict[str, float] = field(default_factory=dict)

    # SaaS cohort mode
    new_logo_arr_per_month: Optional[float] = None
    gross_churn_rate_monthly_pct: Optional[float] = None
    expansion_rate_monthly_pct: Optional[float] = None
    price_escalator_annual_pct: Optional[float] = None


# ── Costs ──

@dataclass
class CostLineAssumption:
    """How to project one cost line (COGS, S&M, R&D, or G&A)."""
    line_item: str                             # "cogs", "sales_marketing", "rd", "ga"
    method: str = "pct_of_revenue"             # "pct_of_revenue" | "fixed" | "headcount"
    pct_of_revenue: Optional[float] = None     # e.g., 26.0 means 26%
    fixed_amount: Optional[float] = None       # $ per month
    annual_escalator_pct: Optional[float] = None  # annual growth on fixed
    headcount: Optional[int] = None
    loaded_cost_per_head: Optional[float] = None  # $ per month per person


@dataclass
class CostAssumptions:
    """All cost assumptions. Either per-line or target margin mode."""
    lines: list[CostLineAssumption] = field(default_factory=list)
    target_ebitda_margin_pct: Optional[float] = None  # back-solve mode


# ── Working Capital ──

@dataclass
class WorkingCapitalAssumptions:
    target_dso: Optional[float] = None  # days
    target_dpo: Optional[float] = None
    target_dio: Optional[float] = None


# ── CapEx ──

@dataclass
class CapExAssumptions:
    maintenance_pct_of_revenue: Optional[float] = None  # e.g., 2.5
    maintenance_fixed: Optional[float] = None           # $ per month
    growth_capex_by_period: dict[str, float] = field(default_factory=dict)


# ── Debt ──

@dataclass
class DebtAssumptions:
    outstanding_balance: float = 0.0
    interest_rate_annual_pct: float = 0.0
    amortization_per_month: float = 0.0
    cash_sweep_pct: float = 0.0  # % of excess cash applied to debt


# ── Tax ──

@dataclass
class TaxAssumptions:
    effective_tax_rate_pct: float = 25.0
    cash_tax_rate_pct: Optional[float] = None


# ── Exit ──

@dataclass
class ExitAssumptions:
    exit_year: int = 5               # years from entry
    exit_multiple: float = 10.0      # EV / EBITDA
    entry_equity: float = 0.0        # $ invested
    entry_date: str = ""             # YYYY-MM


# ── Initiatives ──

@dataclass
class Initiative:
    """A value creation initiative that modifies projected EBITDA."""
    name: str
    ebitda_impact_run_rate: float       # $ per month at full run-rate
    implementation_cost: float = 0.0    # one-time cost in start month
    start_period: str = ""              # YYYY-MM
    ramp_months: int = 1               # months to reach full run-rate
    confidence_pct: float = 100.0       # 0-100
    enabled: bool = True


# ── The Complete Assumption Set ──

@dataclass
class AssumptionSet:
    """A complete set of assumptions for one scenario."""
    name: str = "Base"
    projection_months: int = 36
    revenue: RevenueAssumptions = field(default_factory=RevenueAssumptions)
    costs: CostAssumptions = field(default_factory=CostAssumptions)
    working_capital: WorkingCapitalAssumptions = field(default_factory=WorkingCapitalAssumptions)
    capex: CapExAssumptions = field(default_factory=CapExAssumptions)
    debt: DebtAssumptions = field(default_factory=DebtAssumptions)
    tax: TaxAssumptions = field(default_factory=TaxAssumptions)
    exit_: ExitAssumptions = field(default_factory=ExitAssumptions)
    initiatives: list[Initiative] = field(default_factory=list)


# ── Returns ──

@dataclass
class ReturnsResult:
    """PE return metrics computed from projected financials."""
    entry_equity: float
    exit_ebitda: Optional[float]
    exit_multiple: float
    exit_ev: Optional[float]              # exit_ebitda * exit_multiple
    net_debt_at_exit: Optional[float]
    exit_equity: Optional[float]          # exit_ev - net_debt
    moic: Optional[float]                 # exit_equity / entry_equity
    irr: Optional[float]                  # annualized return
    holding_period_years: float
    value_creation_bridge: list[BridgeComponent] = field(default_factory=list)


# ── Top-Level Model Result ──

@dataclass
class ModelResult:
    """Complete output of the modeling engine."""
    assumptions: AssumptionSet
    combined_data: dict  # str -> NormalizedResult (historical + projected)
    analysis: AnalysisResult
    returns: ReturnsResult | None = None
