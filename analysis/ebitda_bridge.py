"""
Module 1: EBITDA Bridge.

Computes EBITDA bridges (waterfall decompositions):
  A) Month-over-Month (MoM)
  B) Actual vs Budget
  C) Actual vs Prior Year (same month)

Each bridge is verified: component values must sum to total change.
"""

import pandas as pd

from analysis.types import BridgeComponent, EBITDABridge, EBITDABridgeResult
from analysis.utils import get_value, get_period_col, get_prior_year_period


def compute_ebitda_bridges(
    income_df: pd.DataFrame,
    current_period: str | None = None,
) -> EBITDABridgeResult:
    """
    Compute all available EBITDA bridges for the given period.

    Input: Income Statement DataFrame.
    Output: EBITDABridgeResult with MoM, Budget, and PY bridges (each None if not possible).

    Errors: Returns empty result if required data is missing.
    """
    period_col = get_period_col(income_df)
    if period_col not in income_df.columns or "ebitda" not in income_df.columns:
        return EBITDABridgeResult(current_period=current_period or "")

    df = income_df.sort_values(period_col).reset_index(drop=True)

    # Default to last period
    if current_period is None:
        current_period = str(df.iloc[-1][period_col])

    # Find current row
    mask = df[period_col] == current_period
    if mask.sum() == 0:
        return EBITDABridgeResult(current_period=current_period)
    current_idx = df.index[mask][0]
    current_row = df.loc[current_idx]

    # ── Bridge A: MoM ──
    mom = None
    if current_idx > 0:
        prior_row = df.iloc[current_idx - 1]
        mom = _build_full_bridge(
            label="MoM",
            current_row=current_row,
            base_row=prior_row,
            current_period=current_period,
            base_period=str(prior_row[period_col]),
        )

    # ── Bridge B: vs Budget ──
    vs_budget = None
    budget_rev = get_value(current_row, "budget_revenue", default=None)
    budget_ebitda = get_value(current_row, "budget_ebitda", default=None)
    if budget_rev is not None and budget_ebitda is not None and budget_rev > 0:
        vs_budget = _build_budget_bridge(
            current_row=current_row,
            budget_revenue=budget_rev,
            budget_ebitda=budget_ebitda,
            current_period=current_period,
        )

    # ── Bridge C: vs Prior Year ──
    vs_py = None
    py_period = get_prior_year_period(current_period)
    if py_period:
        py_mask = df[period_col] == py_period
        if py_mask.sum() > 0:
            py_row = df.loc[py_mask].iloc[0]
            vs_py = _build_full_bridge(
                label="vs Prior Year",
                current_row=current_row,
                base_row=py_row,
                current_period=current_period,
                base_period=py_period,
            )

    return EBITDABridgeResult(
        current_period=current_period,
        mom=mom,
        vs_budget=vs_budget,
        vs_prior_year=vs_py,
    )


def _build_full_bridge(
    label: str,
    current_row: pd.Series,
    base_row: pd.Series,
    current_period: str,
    base_period: str,
) -> EBITDABridge:
    """
    Build a full EBITDA bridge with per-line-item components.

    Components:
      + Revenue change
      - COGS change (negated: cost increase hurts EBITDA)
      - S&M change
      - R&D change
      - G&A change
    """
    current_ebitda = get_value(current_row, "ebitda")
    base_ebitda = get_value(base_row, "ebitda")

    revenue_impact = get_value(current_row, "revenue") - get_value(base_row, "revenue")
    cogs_impact = -(get_value(current_row, "cogs") - get_value(base_row, "cogs"))
    sm_impact = -(get_value(current_row, "sales_marketing") - get_value(base_row, "sales_marketing"))
    rd_impact = -(get_value(current_row, "rd") - get_value(base_row, "rd"))
    ga_impact = -(get_value(current_row, "ga") - get_value(base_row, "ga"))

    components = [
        BridgeComponent("Revenue", revenue_impact),
        BridgeComponent("COGS", cogs_impact),
        BridgeComponent("Sales & Marketing", sm_impact),
        BridgeComponent("R&D", rd_impact),
        BridgeComponent("G&A", ga_impact),
    ]

    total_change = current_ebitda - base_ebitda
    component_sum = sum(c.value for c in components)
    verification_delta = abs(component_sum - total_change)

    return EBITDABridge(
        label=label,
        base_period=base_period,
        current_period=current_period,
        base_ebitda=base_ebitda,
        current_ebitda=current_ebitda,
        components=components,
        total_change=total_change,
        verification_delta=verification_delta,
        is_verified=verification_delta < 0.01,
    )


def _build_budget_bridge(
    current_row: pd.Series,
    budget_revenue: float,
    budget_ebitda: float,
    current_period: str,
) -> EBITDABridge:
    """
    Build a budget bridge. Budget only provides revenue and EBITDA totals,
    so we decompose into: revenue variance + total cost variance.

    Revenue variance = actual_revenue - budget_revenue
    Cost variance = (budget_ebitda - budget_revenue) - (actual_ebitda - actual_revenue)
                  = budget_total_costs - actual_total_costs (negated)

    Verification: revenue_variance + cost_variance = ebitda_variance
    """
    actual_revenue = get_value(current_row, "revenue")
    actual_ebitda = get_value(current_row, "ebitda")

    revenue_variance = actual_revenue - budget_revenue
    ebitda_variance = actual_ebitda - budget_ebitda

    # Total cost variance = ebitda_variance - revenue_variance
    # This captures all cost impacts in aggregate
    cost_variance = ebitda_variance - revenue_variance

    components = [
        BridgeComponent("Revenue Variance", revenue_variance),
        BridgeComponent("Total Cost Variance", cost_variance),
    ]

    component_sum = sum(c.value for c in components)
    verification_delta = abs(component_sum - ebitda_variance)

    return EBITDABridge(
        label="vs Budget",
        base_period="Budget",
        current_period=current_period,
        base_ebitda=budget_ebitda,
        current_ebitda=actual_ebitda,
        components=components,
        total_change=ebitda_variance,
        verification_delta=verification_delta,
        is_verified=verification_delta < 0.01,
    )
