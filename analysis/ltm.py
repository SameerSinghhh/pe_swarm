"""
Module 8: LTM (Last Twelve Months) Rollups & Rule of 40.

PE firms almost never look at a single month in isolation.
LTM revenue, LTM EBITDA, and LTM margins are the standard view.

Rule of 40: For SaaS companies, revenue growth % + EBITDA margin %.
Above 40 = healthy. Below 40 = concern.
"""

import pandas as pd

from analysis.types import LTMMetrics
from analysis.utils import safe_pct, get_value, get_period_col, get_prior_year_period


def compute_ltm(income_df: pd.DataFrame) -> LTMMetrics | None:
    """
    Compute LTM (trailing 12 months) metrics from Income Statement data.

    Returns None if no data available.
    LTM sums the most recent 12 months (or fewer if less data, noted in months_included).
    """
    period_col = get_period_col(income_df)
    if period_col not in income_df.columns or "revenue" not in income_df.columns:
        return None

    df = income_df.sort_values(period_col).reset_index(drop=True)
    if len(df) == 0:
        return None

    as_of = str(df.iloc[-1][period_col])

    # Take last 12 months (or all if fewer)
    n = min(12, len(df))
    ltm_df = df.tail(n)

    # Sum the key P&L items
    ltm_revenue = ltm_df["revenue"].sum()
    ltm_cogs = ltm_df["cogs"].sum() if "cogs" in ltm_df.columns else None
    ltm_gross_profit = ltm_df["gross_profit"].sum() if "gross_profit" in ltm_df.columns else None
    ltm_ebitda = ltm_df["ebitda"].sum() if "ebitda" in ltm_df.columns else None

    # LTM margins
    ltm_gross_margin = safe_pct(ltm_gross_profit, ltm_revenue) if ltm_gross_profit is not None else None
    ltm_ebitda_margin = safe_pct(ltm_ebitda, ltm_revenue) if ltm_ebitda is not None else None

    # LTM revenue growth (current LTM vs prior LTM)
    ltm_rev_growth = None
    if len(df) >= 24:
        # Full prior LTM available
        prior_ltm_df = df.iloc[-(n + 12):-n]
        prior_ltm_revenue = prior_ltm_df["revenue"].sum()
        ltm_rev_growth = safe_pct(ltm_revenue - prior_ltm_revenue, prior_ltm_revenue)
    elif len(df) >= 13:
        # At least 13 months: can compute approximate YoY
        # Compare last 12 to first N-12 months, annualized
        prior_months = len(df) - n
        if prior_months > 0:
            prior_revenue = df.head(prior_months)["revenue"].sum()
            prior_annualized = prior_revenue * (12 / prior_months)
            ltm_rev_growth = safe_pct(ltm_revenue - prior_annualized, prior_annualized)

    # Rule of 40: revenue growth % + EBITDA margin %
    rule_of_40 = None
    if ltm_rev_growth is not None and ltm_ebitda_margin is not None:
        rule_of_40 = ltm_rev_growth + ltm_ebitda_margin

    return LTMMetrics(
        as_of_period=as_of,
        ltm_revenue=ltm_revenue,
        ltm_cogs=ltm_cogs,
        ltm_gross_profit=ltm_gross_profit,
        ltm_ebitda=ltm_ebitda,
        ltm_gross_margin_pct=round(ltm_gross_margin, 1) if ltm_gross_margin is not None else None,
        ltm_ebitda_margin_pct=round(ltm_ebitda_margin, 1) if ltm_ebitda_margin is not None else None,
        ltm_revenue_growth_yoy=round(ltm_rev_growth, 1) if ltm_rev_growth is not None else None,
        rule_of_40=round(rule_of_40, 1) if rule_of_40 is not None else None,
        months_included=n,
    )
