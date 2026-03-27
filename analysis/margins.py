"""
Module 3: Margin & Growth Calculations.

Computes all margin percentages and growth rates for every period
in the Income Statement. Pure arithmetic — no AI, no assumptions.
"""

import pandas as pd

from analysis.types import PeriodMargins, MarginsResult
from analysis.utils import safe_pct, get_value, get_period_col, get_prior_year_period


def compute_margins(income_df: pd.DataFrame) -> MarginsResult:
    """
    Compute all margins and growth rates for every period.

    Input: Income Statement DataFrame with columns:
        period, revenue, cogs, gross_profit, sales_marketing, rd, ga, total_opex, ebitda

    Output: MarginsResult with one PeriodMargins per row, plus a convenience DataFrame.

    Errors: Returns empty MarginsResult if input is missing required columns.
    """
    period_col = get_period_col(income_df)
    if period_col not in income_df.columns or "revenue" not in income_df.columns:
        return MarginsResult(periods=[], as_dataframe=pd.DataFrame())

    df = income_df.sort_values(period_col).reset_index(drop=True)
    periods = []

    for i, row in df.iterrows():
        period = str(row[period_col])
        revenue = get_value(row, "revenue")
        gross_profit = get_value(row, "gross_profit")
        ebitda = get_value(row, "ebitda")
        sales_marketing = get_value(row, "sales_marketing")
        rd = get_value(row, "rd") if "rd" in df.columns else None
        ga = get_value(row, "ga") if "ga" in df.columns else None
        total_opex = get_value(row, "total_opex")

        # Margins
        gross_margin_pct = safe_pct(gross_profit, revenue)
        ebitda_margin_pct = safe_pct(ebitda, revenue)
        sm_pct = safe_pct(sales_marketing, revenue)
        rd_pct = safe_pct(rd, revenue) if rd is not None else None
        ga_pct = safe_pct(ga, revenue) if ga is not None else None
        opex_pct = safe_pct(total_opex, revenue)

        # MoM growth
        revenue_growth_mom = None
        ebitda_growth_mom = None
        if i > 0:
            prior = df.iloc[i - 1]
            prior_rev = get_value(prior, "revenue")
            prior_ebitda = get_value(prior, "ebitda")
            revenue_growth_mom = safe_pct(revenue - prior_rev, prior_rev)
            ebitda_growth_mom = safe_pct(ebitda - prior_ebitda, prior_ebitda)

        # YoY growth
        revenue_growth_yoy = None
        ebitda_growth_yoy = None
        py_period = get_prior_year_period(period)
        if py_period:
            py_mask = df[period_col] == py_period
            if py_mask.sum() > 0:
                py_row = df.loc[py_mask].iloc[0]
                py_rev = get_value(py_row, "revenue")
                py_ebitda = get_value(py_row, "ebitda")
                revenue_growth_yoy = safe_pct(revenue - py_rev, py_rev)
                ebitda_growth_yoy = safe_pct(ebitda - py_ebitda, py_ebitda)

        periods.append(PeriodMargins(
            period=period,
            gross_margin_pct=gross_margin_pct,
            ebitda_margin_pct=ebitda_margin_pct,
            sm_pct_revenue=sm_pct,
            rd_pct_revenue=rd_pct,
            ga_pct_revenue=ga_pct,
            opex_pct_revenue=opex_pct,
            revenue_growth_mom=revenue_growth_mom,
            revenue_growth_yoy=revenue_growth_yoy,
            ebitda_growth_mom=ebitda_growth_mom,
            ebitda_growth_yoy=ebitda_growth_yoy,
        ))

    # Build convenience DataFrame
    records = []
    for p in periods:
        records.append({
            "period": p.period,
            "gross_margin_pct": p.gross_margin_pct,
            "ebitda_margin_pct": p.ebitda_margin_pct,
            "sm_pct_revenue": p.sm_pct_revenue,
            "rd_pct_revenue": p.rd_pct_revenue,
            "ga_pct_revenue": p.ga_pct_revenue,
            "opex_pct_revenue": p.opex_pct_revenue,
            "revenue_growth_mom": p.revenue_growth_mom,
            "revenue_growth_yoy": p.revenue_growth_yoy,
            "ebitda_growth_mom": p.ebitda_growth_mom,
            "ebitda_growth_yoy": p.ebitda_growth_yoy,
        })

    return MarginsResult(
        periods=periods,
        as_dataframe=pd.DataFrame(records),
    )
