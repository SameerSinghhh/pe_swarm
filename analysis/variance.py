"""
Module 2: Three-Way Variance Analysis.

For every P&L line item, computes:
  - Actual vs Budget
  - Actual vs Prior Month
  - Actual vs Prior Year (same month)

Each variance includes: dollar change, % change, as % of revenue, favorability.
"""

import pandas as pd

from analysis.types import LineVariance, PeriodVariance, VarianceResult, Favorability
from analysis.utils import safe_pct, get_value, get_period_col, get_prior_year_period, favorability


# P&L lines to analyze (in display order)
PL_LINES = [
    "revenue",
    "cogs",
    "gross_profit",
    "sales_marketing",
    "rd",
    "ga",
    "total_opex",
    "ebitda",
]


def compute_variance(income_df: pd.DataFrame) -> VarianceResult:
    """
    Compute three-way variance for every P&L line item, for every period.

    Input: Income Statement DataFrame.
    Output: VarianceResult with one PeriodVariance per row.

    Errors: Gracefully skips lines not present in the data.
    """
    period_col = get_period_col(income_df)
    if period_col not in income_df.columns:
        return VarianceResult(periods=[])

    df = income_df.sort_values(period_col).reset_index(drop=True)

    # Determine which lines are available
    available_lines = [line for line in PL_LINES if line in df.columns]
    if not available_lines:
        return VarianceResult(periods=[])

    periods = []

    for i, row in df.iterrows():
        period = str(row[period_col])
        current_revenue = get_value(row, "revenue")

        # ── vs Budget ──
        vs_budget = None
        if "budget_revenue" in df.columns or "budget_ebitda" in df.columns:
            budget_rev = get_value(row, "budget_revenue", default=None)
            budget_ebitda = get_value(row, "budget_ebitda", default=None)
            if budget_rev is not None or budget_ebitda is not None:
                vs_budget = []
                for line in available_lines:
                    budget_val = _get_budget_value(row, line)
                    if budget_val is not None:
                        actual = get_value(row, line)
                        vs_budget.append(_make_variance(
                            line, actual, budget_val, current_revenue
                        ))

        # ── vs Prior Month ──
        vs_prior_month = None
        if i > 0:
            prior_row = df.iloc[i - 1]
            vs_prior_month = []
            for line in available_lines:
                actual = get_value(row, line)
                comparator = get_value(prior_row, line)
                vs_prior_month.append(_make_variance(
                    line, actual, comparator, current_revenue
                ))

        # ── vs Prior Year ──
        vs_prior_year = None
        py_period = get_prior_year_period(period)
        if py_period:
            py_mask = df[period_col] == py_period
            if py_mask.sum() > 0:
                py_row = df.loc[py_mask].iloc[0]
                vs_prior_year = []
                for line in available_lines:
                    actual = get_value(row, line)
                    comparator = get_value(py_row, line)
                    vs_prior_year.append(_make_variance(
                        line, actual, comparator, current_revenue
                    ))

        periods.append(PeriodVariance(
            period=period,
            vs_budget=vs_budget if vs_budget else None,
            vs_prior_month=vs_prior_month,
            vs_prior_year=vs_prior_year,
        ))

    return VarianceResult(periods=periods)


def _make_variance(
    line_item: str,
    actual: float,
    comparator: float,
    current_revenue: float,
) -> LineVariance:
    """Create a LineVariance for one line item against one comparator."""
    dollar_change = actual - comparator
    pct_change = safe_pct(dollar_change, comparator)
    as_pct_of_revenue = safe_pct(dollar_change, current_revenue)
    fav = favorability(line_item, dollar_change)

    return LineVariance(
        line_item=line_item,
        actual=actual,
        comparator=comparator,
        dollar_change=dollar_change,
        pct_change=pct_change,
        as_pct_of_revenue=as_pct_of_revenue,
        favorable=fav,
    )


def _get_budget_value(row: pd.Series, line: str) -> float | None:
    """
    Get the budget value for a P&L line. Budget data typically only
    provides revenue and EBITDA — other lines return None.
    """
    if line == "revenue":
        val = get_value(row, "budget_revenue", default=None)
        return val
    elif line == "ebitda":
        val = get_value(row, "budget_ebitda", default=None)
        return val
    else:
        return None
