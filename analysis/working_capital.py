"""
Module 4: Working Capital Analytics.

Computes DSO, DPO, DIO, Cash Conversion Cycle, working capital changes,
DSO cash impact, and AR aging distribution.

Two paths:
  1. Direct: working_capital_df provides DSO/DPO/DIO directly
  2. Calculated: from balance sheet + income statement
"""

import pandas as pd

from analysis.types import PeriodWorkingCapital, WorkingCapitalResult, ARAgingPcts
from analysis.utils import safe_div, safe_pct, days_in_period, get_value, has_column


def compute_working_capital(
    balance_sheet_df: pd.DataFrame | None = None,
    income_df: pd.DataFrame | None = None,
    working_capital_df: pd.DataFrame | None = None,
) -> WorkingCapitalResult:
    """
    Compute working capital metrics.

    Uses working_capital_df directly if available, otherwise calculates
    from balance sheet + income statement joined on period.

    Input: Any combination of the three DataFrames.
    Output: WorkingCapitalResult with one PeriodWorkingCapital per period.
    """
    # Path 1: Direct from working capital data
    if working_capital_df is not None and "period" in working_capital_df.columns:
        return _from_working_capital_df(working_capital_df)

    # Path 2: Calculate from BS + IS
    if balance_sheet_df is not None and income_df is not None:
        return _from_bs_and_is(balance_sheet_df, income_df)

    return WorkingCapitalResult(periods=[])


def _from_working_capital_df(wc_df: pd.DataFrame) -> WorkingCapitalResult:
    """Compute from working capital / AR-AP aging data directly."""
    df = wc_df.sort_values("period").reset_index(drop=True)
    periods = []

    for i, row in df.iterrows():
        period = str(row["period"])

        # DSO, DPO, DIO from data
        dso = get_value(row, "dso", default=None)
        dpo = get_value(row, "dpo", default=None)
        dio = get_value(row, "dio", default=None)

        # CCC
        ccc = None
        if dso is not None and dpo is not None:
            dio_val = dio if dio is not None else 0
            ccc = dso + dio_val - dpo

        # WC change (from AR/AP totals)
        wc_change = None
        if i > 0:
            prior = df.iloc[i - 1]
            ar_delta = get_value(row, "ar_total", 0) - get_value(prior, "ar_total", 0)
            ap_delta = get_value(row, "ap_total", 0) - get_value(prior, "ap_total", 0)
            inv_delta = get_value(row, "inventory_total", 0) - get_value(prior, "inventory_total", 0)
            wc_change = ar_delta + inv_delta - ap_delta

        # DSO cash impact
        dso_cash_impact = None
        if i > 0 and dso is not None:
            prior_dso = get_value(df.iloc[i - 1], "dso", default=None)
            if prior_dso is not None:
                # Revenue proxy: ar_total / (dso / days)
                days = days_in_period(period)
                ar_total = get_value(row, "ar_total", 0)
                if dso > 0:
                    implied_revenue = ar_total / (dso / days)
                    dso_change = dso - prior_dso
                    dso_cash_impact = -(dso_change / days) * implied_revenue

        # AR aging
        ar_aging = _compute_ar_aging(row)

        periods.append(PeriodWorkingCapital(
            period=period,
            dso=dso,
            dpo=dpo,
            dio=dio,
            ccc=ccc,
            wc_change=wc_change,
            dso_cash_impact=dso_cash_impact,
            ar_aging=ar_aging,
        ))

    return WorkingCapitalResult(periods=periods)


def _from_bs_and_is(
    balance_sheet_df: pd.DataFrame,
    income_df: pd.DataFrame,
) -> WorkingCapitalResult:
    """Calculate working capital metrics from balance sheet + income statement."""
    bs = balance_sheet_df.sort_values("period").reset_index(drop=True)
    is_df = income_df.sort_values("period" if "period" in income_df.columns else "month").reset_index(drop=True)

    # Normalize period column name
    is_period_col = "period" if "period" in is_df.columns else "month"
    is_df = is_df.rename(columns={is_period_col: "period"}) if is_period_col != "period" else is_df

    # Join on period
    merged = pd.merge(bs, is_df[["period", "revenue", "cogs"]], on="period", how="inner")
    merged = merged.sort_values("period").reset_index(drop=True)

    periods = []

    for i, row in merged.iterrows():
        period = str(row["period"])
        revenue = get_value(row, "revenue")
        cogs = get_value(row, "cogs")
        days = days_in_period(period)

        # DSO = (AR / Revenue) * days
        ar = get_value(row, "accounts_receivable", default=None)
        dso = None
        if ar is not None and revenue > 0:
            dso = (ar / revenue) * days

        # DPO = (AP / COGS) * days
        ap = get_value(row, "accounts_payable", default=None)
        dpo = None
        if ap is not None and cogs > 0:
            dpo = (ap / cogs) * days

        # DIO = (Inventory / COGS) * days
        inventory = get_value(row, "inventory", default=None)
        dio = None
        if inventory is not None and cogs > 0:
            dio = (inventory / cogs) * days

        # CCC = DSO + DIO - DPO
        ccc = None
        if dso is not None and dpo is not None:
            dio_val = dio if dio is not None else 0
            ccc = dso + dio_val - dpo

        # Working capital change
        wc_change = None
        if i > 0:
            prior = merged.iloc[i - 1]
            ar_delta = get_value(row, "accounts_receivable", 0) - get_value(prior, "accounts_receivable", 0)
            inv_delta = get_value(row, "inventory", 0) - get_value(prior, "inventory", 0)
            prepaid_delta = get_value(row, "prepaid_expenses", 0) - get_value(prior, "prepaid_expenses", 0)
            other_ca_delta = get_value(row, "other_current_assets", 0) - get_value(prior, "other_current_assets", 0)
            ap_delta = get_value(row, "accounts_payable", 0) - get_value(prior, "accounts_payable", 0)
            accrued_delta = get_value(row, "accrued_liabilities", 0) - get_value(prior, "accrued_liabilities", 0)
            other_cl_delta = get_value(row, "other_current_liabilities", 0) - get_value(prior, "other_current_liabilities", 0)

            wc_change = (ar_delta + inv_delta + prepaid_delta + other_ca_delta
                        - ap_delta - accrued_delta - other_cl_delta)

        # DSO cash impact
        dso_cash_impact = None
        if i > 0 and dso is not None:
            prior_row = merged.iloc[i - 1]
            prior_ar = get_value(prior_row, "accounts_receivable", default=None)
            prior_rev = get_value(prior_row, "revenue")
            prior_days = days_in_period(str(prior_row["period"]))
            if prior_ar is not None and prior_rev > 0:
                prior_dso = (prior_ar / prior_rev) * prior_days
                dso_change = dso - prior_dso
                dso_cash_impact = -(dso_change / days) * revenue

        periods.append(PeriodWorkingCapital(
            period=period,
            dso=round(dso, 1) if dso is not None else None,
            dpo=round(dpo, 1) if dpo is not None else None,
            dio=round(dio, 1) if dio is not None else None,
            ccc=round(ccc, 1) if ccc is not None else None,
            wc_change=wc_change,
            dso_cash_impact=dso_cash_impact,
            ar_aging=None,
        ))

    return WorkingCapitalResult(periods=periods)


def _compute_ar_aging(row: pd.Series) -> ARAgingPcts | None:
    """Compute AR aging distribution from aging bucket columns."""
    ar_total = get_value(row, "ar_total", default=None)
    if ar_total is None or ar_total == 0:
        return None

    return ARAgingPcts(
        current_pct=safe_pct(get_value(row, "ar_current", 0), ar_total),
        pct_31_60=safe_pct(get_value(row, "ar_31_60", 0), ar_total),
        pct_61_90=safe_pct(get_value(row, "ar_61_90", 0), ar_total),
        pct_91_120=safe_pct(get_value(row, "ar_91_120", 0), ar_total),
        over_120_pct=safe_pct(get_value(row, "ar_over_120", 0), ar_total),
    )
