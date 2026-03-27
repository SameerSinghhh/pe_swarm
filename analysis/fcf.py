"""
Module 5: Free Cash Flow & Cash Conversion.

Computes FCF, cash conversion ratio, net debt, and leverage metrics.
Works with cash flow statement + income statement + balance sheet.
"""

import pandas as pd

from analysis.types import PeriodFCF, FCFResult
from analysis.utils import safe_div, get_value, has_column


def compute_fcf(
    cash_flow_df: pd.DataFrame | None = None,
    income_df: pd.DataFrame | None = None,
    balance_sheet_df: pd.DataFrame | None = None,
) -> FCFResult:
    """
    Compute FCF and leverage metrics.

    Primary path: From cash flow statement (FCF = CFO + CapEx).
    Leverage: From balance sheet (net debt / LTM EBITDA).
    Cash conversion: FCF / EBITDA (needs both CF and IS).

    Input: Any combination of DataFrames.
    Output: FCFResult with one PeriodFCF per period.
    """
    if cash_flow_df is None or "period" not in cash_flow_df.columns:
        return FCFResult(periods=[])

    cf = cash_flow_df.sort_values("period").reset_index(drop=True)

    # Build period-keyed lookup for income and balance sheet data
    is_lookup = _build_lookup(income_df)
    bs_lookup = _build_lookup(balance_sheet_df)

    # For LTM EBITDA: collect all available EBITDA values
    ebitda_series = {}
    if income_df is not None:
        pcol = "period" if "period" in income_df.columns else "month"
        for _, row in income_df.iterrows():
            p = str(row[pcol])
            ebitda_series[p] = get_value(row, "ebitda")

    periods = []

    for i, row in cf.iterrows():
        period = str(row["period"])

        # FCF = cash_from_operations + capex (capex is negative)
        cfo = get_value(row, "cash_from_operations", default=None)
        capex = get_value(row, "capex", default=None)

        fcf = None
        if cfo is not None and capex is not None:
            fcf = cfo + capex
        elif has_column(cf, "free_cash_flow"):
            fcf = get_value(row, "free_cash_flow", default=None)

        # Cash conversion = FCF / EBITDA
        ebitda = None
        if period in is_lookup:
            ebitda = get_value(is_lookup[period], "ebitda", default=None)
        cash_conversion = safe_div(fcf, ebitda) if fcf is not None and ebitda is not None else None

        # Net debt from balance sheet
        net_debt = None
        if period in bs_lookup:
            bs_row = bs_lookup[period]
            std = get_value(bs_row, "short_term_debt", 0)
            ltd = get_value(bs_row, "long_term_debt", 0)
            cash = get_value(bs_row, "cash", 0)
            net_debt = std + ltd - cash

        # LTM EBITDA (trailing 12 months sum)
        ltm_ebitda = _compute_ltm_ebitda(period, ebitda_series)

        # Net debt / LTM EBITDA
        nd_to_ebitda = safe_div(net_debt, ltm_ebitda) if net_debt is not None and ltm_ebitda is not None else None

        periods.append(PeriodFCF(
            period=period,
            free_cash_flow=fcf,
            cash_conversion_ratio=round(cash_conversion, 3) if cash_conversion is not None else None,
            net_debt=net_debt,
            ltm_ebitda=ltm_ebitda,
            net_debt_to_ltm_ebitda=round(nd_to_ebitda, 2) if nd_to_ebitda is not None else None,
        ))

    return FCFResult(periods=periods)


def _build_lookup(df: pd.DataFrame | None) -> dict[str, pd.Series]:
    """Build a period → row lookup dict."""
    if df is None:
        return {}
    pcol = "period" if "period" in df.columns else "month"
    if pcol not in df.columns:
        return {}
    lookup = {}
    for _, row in df.iterrows():
        lookup[str(row[pcol])] = row
    return lookup


def _compute_ltm_ebitda(current_period: str, ebitda_series: dict[str, float]) -> float | None:
    """Compute last-twelve-months EBITDA sum from available data."""
    if not ebitda_series:
        return None

    try:
        parts = current_period.split("-")
        year = int(parts[0])
        month = int(parts[1])
    except (ValueError, IndexError):
        return None

    # Collect up to 12 months ending at current_period
    total = 0.0
    count = 0
    for m_offset in range(12):
        m = month - m_offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        p = f"{y}-{m:02d}"
        if p in ebitda_series:
            total += ebitda_series[p]
            count += 1

    if count == 0:
        return None

    # If we have fewer than 12 months, annualize
    if count < 12:
        total = total * (12 / count)

    return total
