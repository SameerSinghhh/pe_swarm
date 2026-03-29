"""
Auto-suggestion engine. Reads historical data and proposes sensible
default assumptions. Pure math — no LLM.

The analyst starts from these defaults and adjusts what they disagree with,
instead of filling everything from scratch.
"""

import pandas as pd

from core.result import NormalizedResult
from modeling.types import (
    AssumptionSet, RevenueAssumptions, CostAssumptions, CostLineAssumption,
    WorkingCapitalAssumptions, CapExAssumptions, DebtAssumptions,
    TaxAssumptions, ExitAssumptions,
)
from analysis.utils import safe_div, get_period_col


def suggest_assumptions(
    historical: dict[str, NormalizedResult],
    lookback_months: int = 6,
) -> AssumptionSet:
    """
    Generate default assumptions from historical data.

    Reads the last `lookback_months` of each data type and computes
    sensible defaults. Returns an AssumptionSet the analyst can tweak.
    """
    assumptions = AssumptionSet(name="Base", projection_months=12)

    # ── Revenue assumptions from P&L ──
    if "income_statement" in historical:
        is_df = _get_sorted_df(historical["income_statement"].df)
        assumptions.revenue = _suggest_revenue(is_df, lookback_months)
        assumptions.costs = _suggest_costs(is_df, lookback_months)

    # ── Working capital from WC data or Balance Sheet ──
    if "working_capital" in historical:
        wc_df = _get_sorted_df(historical["working_capital"].df)
        assumptions.working_capital = _suggest_wc_from_wc(wc_df)
    elif "balance_sheet" in historical and "income_statement" in historical:
        bs_df = _get_sorted_df(historical["balance_sheet"].df)
        is_df = _get_sorted_df(historical["income_statement"].df)
        assumptions.working_capital = _suggest_wc_from_bs(bs_df, is_df)

    # ── Debt from Balance Sheet ──
    if "balance_sheet" in historical:
        bs_df = _get_sorted_df(historical["balance_sheet"].df)
        assumptions.debt = _suggest_debt(bs_df, historical.get("cash_flow"))

    # ── CapEx from Cash Flow ──
    if "cash_flow" in historical and "income_statement" in historical:
        cf_df = _get_sorted_df(historical["cash_flow"].df)
        is_df = _get_sorted_df(historical["income_statement"].df)
        assumptions.capex = _suggest_capex(cf_df, is_df, lookback_months)

    # ── Defaults that need human input ──
    assumptions.tax = TaxAssumptions(effective_tax_rate_pct=25.0)
    assumptions.exit_ = ExitAssumptions(exit_year=5, exit_multiple=10.0)

    return assumptions


def _get_sorted_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sort DataFrame by period column."""
    pcol = get_period_col(df)
    return df.sort_values(pcol).reset_index(drop=True)


def _suggest_revenue(is_df: pd.DataFrame, lookback: int) -> RevenueAssumptions:
    """Suggest revenue growth from P&L history."""
    recent = is_df.tail(lookback)

    if len(recent) < 2:
        return RevenueAssumptions(method="growth_rate", growth_rate_pct=0.0)

    # Compute MoM growth rates
    growth_rates = recent["revenue"].pct_change().dropna() * 100

    if len(growth_rates) == 0:
        return RevenueAssumptions(method="growth_rate", growth_rate_pct=0.0)

    # Use median (resistant to outliers like a bad month)
    median_growth = float(growth_rates.median())

    # Cap at 0 minimum — don't auto-suggest decline
    median_growth = max(0.0, median_growth)

    return RevenueAssumptions(
        method="growth_rate",
        growth_rate_pct=round(median_growth, 1),
        growth_period="mom",
    )


def _suggest_costs(is_df: pd.DataFrame, lookback: int) -> CostAssumptions:
    """Suggest cost assumptions as % of revenue from P&L history."""
    recent = is_df.tail(lookback)
    lines = []

    for line_item, col in [
        ("cogs", "cogs"),
        ("sales_marketing", "sales_marketing"),
        ("rd", "rd"),
        ("ga", "ga"),
    ]:
        if col not in recent.columns:
            continue

        # Compute ratio for each month, take mean
        mask = recent["revenue"] > 0
        if mask.sum() == 0:
            continue

        ratios = recent.loc[mask, col] / recent.loc[mask, "revenue"] * 100
        avg_pct = float(ratios.mean())

        lines.append(CostLineAssumption(
            line_item=line_item,
            method="pct_of_revenue",
            pct_of_revenue=round(avg_pct, 1),
        ))

    return CostAssumptions(lines=lines)


def _suggest_wc_from_wc(wc_df: pd.DataFrame) -> WorkingCapitalAssumptions:
    """Suggest WC targets from working capital data (has DSO/DPO directly)."""
    last = wc_df.iloc[-1]

    dso = float(last.get("dso", 0)) if pd.notna(last.get("dso")) else None
    dpo = float(last.get("dpo", 0)) if pd.notna(last.get("dpo")) else None
    dio = float(last.get("dio", 0)) if pd.notna(last.get("dio")) else None

    return WorkingCapitalAssumptions(
        target_dso=dso,
        target_dpo=dpo,
        target_dio=dio,
    )


def _suggest_wc_from_bs(bs_df: pd.DataFrame, is_df: pd.DataFrame) -> WorkingCapitalAssumptions:
    """Calculate DSO/DPO from balance sheet + P&L."""
    # Join on period
    pcol_bs = get_period_col(bs_df)
    pcol_is = get_period_col(is_df)

    merged = pd.merge(
        bs_df[[pcol_bs, "accounts_receivable", "accounts_payable"]].rename(columns={pcol_bs: "period"}),
        is_df[[pcol_is, "revenue", "cogs"]].rename(columns={pcol_is: "period"}),
        on="period",
        how="inner",
    )

    if merged.empty:
        return WorkingCapitalAssumptions()

    last = merged.iloc[-1]
    rev = float(last.get("revenue", 0))
    cogs = float(last.get("cogs", 0))
    ar = float(last.get("accounts_receivable", 0))
    ap = float(last.get("accounts_payable", 0))

    # Approximate days using 30-day month
    dso = safe_div(ar, rev) * 30 if rev > 0 else None
    dpo = safe_div(ap, cogs) * 30 if cogs > 0 else None

    return WorkingCapitalAssumptions(
        target_dso=round(dso, 0) if dso else None,
        target_dpo=round(dpo, 0) if dpo else None,
    )


def _suggest_debt(bs_df: pd.DataFrame, cf_result: NormalizedResult | None) -> DebtAssumptions:
    """Suggest debt assumptions from balance sheet + cash flow."""
    last = bs_df.iloc[-1]

    std = float(last.get("short_term_debt", 0) or 0)
    ltd = float(last.get("long_term_debt", 0) or 0)
    balance = std + ltd

    # Amortization from cash flow
    amort = 0.0
    if cf_result is not None:
        cf_df = _get_sorted_df(cf_result.df)
        if "debt_repaid" in cf_df.columns:
            repayments = cf_df["debt_repaid"].dropna().abs()
            if len(repayments) > 0:
                amort = float(repayments.mean())

    return DebtAssumptions(
        outstanding_balance=balance,
        amortization_per_month=round(amort, 0),
    )


def _suggest_capex(cf_df: pd.DataFrame, is_df: pd.DataFrame, lookback: int) -> CapExAssumptions:
    """Suggest CapEx as % of revenue from cash flow + P&L."""
    pcol_cf = get_period_col(cf_df)
    pcol_is = get_period_col(is_df)

    merged = pd.merge(
        cf_df[[pcol_cf, "capex"]].rename(columns={pcol_cf: "period"}),
        is_df[[pcol_is, "revenue"]].rename(columns={pcol_is: "period"}),
        on="period",
        how="inner",
    )

    if merged.empty:
        return CapExAssumptions()

    recent = merged.tail(lookback)
    mask = recent["revenue"] > 0
    if mask.sum() == 0:
        return CapExAssumptions()

    # CapEx is typically negative in the data
    capex_pct = (recent.loc[mask, "capex"].abs() / recent.loc[mask, "revenue"] * 100).mean()

    return CapExAssumptions(
        maintenance_pct_of_revenue=round(float(capex_pct), 1),
    )
