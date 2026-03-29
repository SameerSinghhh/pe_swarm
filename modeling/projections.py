"""
Projection engine. Takes historical data + assumptions → projected DataFrames.

Projected DataFrames use the EXACT same column schema as ingested data.
This means the existing analysis engine works on them with zero changes.
"""

import calendar
import copy
from typing import Optional

import pandas as pd

from core.result import NormalizedResult
from modeling.types import AssumptionSet, CostLineAssumption
from modeling.initiatives import apply_initiatives
from analysis.utils import safe_div, days_in_period


def project(
    historical: dict[str, NormalizedResult],
    assumptions: AssumptionSet,
) -> dict[str, NormalizedResult]:
    """
    Project forward from historical data using the given assumptions.

    Returns a new dict of NormalizedResult objects where each DataFrame
    contains historical rows + projected rows, with _is_projected column.
    """
    result = {}

    # Project income statement (always — it's the foundation)
    if "income_statement" in historical:
        is_result = historical["income_statement"]
        projected_is_df = project_income_statement(is_result.df, assumptions)
        result["income_statement"] = NormalizedResult(
            df=projected_is_df,
            doc_type="income_statement",
            doc_type_name="Income Statement / P&L (Projected)",
        )

    # Project BS + CF if historical data available
    if "balance_sheet" in historical and "income_statement" in result:
        projected_is_df = result["income_statement"].df
        historical_bs = historical["balance_sheet"].df
        historical_cf = historical.get("cash_flow", NormalizedResult(df=pd.DataFrame())).df

        bs_df, cf_df = project_bs_and_cf(
            historical_bs=historical_bs,
            historical_cf=historical_cf,
            projected_is=projected_is_df,
            assumptions=assumptions,
        )

        result["balance_sheet"] = NormalizedResult(
            df=bs_df,
            doc_type="balance_sheet",
            doc_type_name="Balance Sheet (Projected)",
        )
        result["cash_flow"] = NormalizedResult(
            df=cf_df,
            doc_type="cash_flow",
            doc_type_name="Cash Flow Statement (Projected)",
        )

    # Copy through any data types we don't project (they still get used by analysis)
    for doc_type, nr in historical.items():
        if doc_type not in result:
            df = nr.df.copy()
            df["_is_projected"] = False
            result[doc_type] = NormalizedResult(
                df=df,
                doc_type=nr.doc_type,
                doc_type_name=nr.doc_type_name,
                company_name=nr.company_name,
            )

    return result


def project_income_statement(
    historical_df: pd.DataFrame,
    assumptions: AssumptionSet,
) -> pd.DataFrame:
    """
    Project the income statement forward from the last historical month.

    Returns combined DataFrame: historical + projected rows.
    All projected rows have _is_projected = True.
    """
    period_col = "period" if "period" in historical_df.columns else "month"
    df = historical_df.sort_values(period_col).reset_index(drop=True)

    # Mark historical rows
    df["_is_projected"] = False

    last_period = str(df.iloc[-1][period_col])
    last_row = df.iloc[-1]

    # Get the last period's cost structure for defaults
    last_revenue = float(last_row.get("revenue", 0))
    last_cogs = float(last_row.get("cogs", 0))
    last_sm = float(last_row.get("sales_marketing", 0))
    last_rd = float(last_row.get("rd", 0)) if "rd" in df.columns else 0
    last_ga = float(last_row.get("ga", 0)) if "ga" in df.columns else 0
    last_ebitda = float(last_row.get("ebitda", 0))

    # Default cost ratios from last historical period
    default_cogs_pct = safe_div(last_cogs, last_revenue) if last_revenue else 0.26
    default_sm_pct = safe_div(last_sm, last_revenue) if last_revenue else 0.35
    default_rd_pct = safe_div(last_rd, last_revenue) if last_revenue else 0.18
    default_ga_pct = safe_div(last_ga, last_revenue) if last_revenue else 0.12

    # For SaaS cohort mode: starting MRR
    current_mrr = last_revenue

    projected_rows = []
    prev_revenue = last_revenue
    prev_period = last_period

    for m in range(assumptions.projection_months):
        period = _next_period(prev_period)

        # ── Revenue ──
        revenue = _project_revenue(
            assumptions.revenue, period, prev_revenue, current_mrr, m
        )

        # Update MRR for SaaS mode
        if assumptions.revenue.method == "saas_cohort":
            current_mrr = revenue

        # ── Costs ──
        cogs, sm, rd, ga = _project_costs(
            assumptions.costs, revenue, m,
            default_cogs_pct, default_sm_pct, default_rd_pct, default_ga_pct,
            last_sm, last_rd, last_ga, last_cogs,
        )

        # ── Derived fields ──
        gross_profit = revenue - cogs
        total_opex = sm + rd + ga
        ebitda = gross_profit - total_opex

        # ── Apply initiatives ──
        ebitda_adj, impl_cost = apply_initiatives(ebitda, period, assumptions.initiatives)
        ebitda = ebitda_adj
        # Implementation cost reduces EBITDA further
        ebitda -= impl_cost

        # Recalculate total_opex to keep P&L consistent
        total_opex = gross_profit - ebitda

        row = {
            period_col: period,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "sales_marketing": sm,
            "rd": rd,
            "ga": ga,
            "total_opex": total_opex,
            "ebitda": ebitda,
            "_is_projected": True,
        }

        projected_rows.append(row)
        prev_revenue = revenue
        prev_period = period

    projected_df = pd.DataFrame(projected_rows)
    combined = pd.concat([df, projected_df], ignore_index=True)

    return combined


def _project_revenue(
    rev_assumptions,
    period: str,
    prev_revenue: float,
    current_mrr: float,
    month_index: int,
) -> float:
    """Project revenue for one month using the chosen method."""
    method = rev_assumptions.method

    if method == "target" and period in rev_assumptions.target_by_period:
        return rev_assumptions.target_by_period[period]

    elif method == "growth_rate":
        rate = rev_assumptions.growth_rate_pct or 0.0
        return prev_revenue * (1 + rate / 100)

    elif method == "saas_cohort":
        new_arr = rev_assumptions.new_logo_arr_per_month or 0
        churn_pct = (rev_assumptions.gross_churn_rate_monthly_pct or 0) / 100
        expansion_pct = (rev_assumptions.expansion_rate_monthly_pct or 0) / 100

        churned = current_mrr * churn_pct
        expanded = current_mrr * expansion_pct
        return current_mrr - churned + expanded + new_arr

    else:
        # Default: flat
        return prev_revenue


def _project_costs(
    cost_assumptions,
    revenue: float,
    month_index: int,
    default_cogs_pct,
    default_sm_pct,
    default_rd_pct,
    default_ga_pct,
    last_sm,
    last_rd,
    last_ga,
    last_cogs,
) -> tuple[float, float, float, float]:
    """Project all cost lines for one month."""

    # Target EBITDA margin mode: back-solve total costs
    if cost_assumptions.target_ebitda_margin_pct is not None:
        target_margin = cost_assumptions.target_ebitda_margin_pct / 100
        target_ebitda = revenue * target_margin
        # Assume COGS stays at historical ratio, back-solve opex
        cogs = revenue * (default_cogs_pct or 0.26)
        gross_profit = revenue - cogs
        total_opex = gross_profit - target_ebitda
        # Distribute opex in historical proportions
        total_last_opex = last_sm + last_rd + last_ga
        if total_last_opex > 0:
            sm = total_opex * (last_sm / total_last_opex)
            rd = total_opex * (last_rd / total_last_opex)
            ga = total_opex * (last_ga / total_last_opex)
        else:
            sm = total_opex * 0.5
            rd = total_opex * 0.3
            ga = total_opex * 0.2
        return cogs, sm, rd, ga

    # Per-line mode
    cost_map = {cl.line_item: cl for cl in cost_assumptions.lines}

    cogs = _project_one_cost(cost_map.get("cogs"), revenue, month_index,
                              default_cogs_pct, last_cogs)
    sm = _project_one_cost(cost_map.get("sales_marketing"), revenue, month_index,
                            default_sm_pct, last_sm)
    rd = _project_one_cost(cost_map.get("rd"), revenue, month_index,
                            default_rd_pct, last_rd)
    ga = _project_one_cost(cost_map.get("ga"), revenue, month_index,
                            default_ga_pct, last_ga)

    return cogs, sm, rd, ga


def _project_one_cost(
    assumption: CostLineAssumption | None,
    revenue: float,
    month_index: int,
    default_pct: float | None,
    last_value: float,
) -> float:
    """Project one cost line for one month."""
    if assumption is None:
        # No explicit assumption — use historical ratio
        if default_pct is not None:
            return revenue * default_pct
        return last_value

    if assumption.method == "pct_of_revenue":
        pct = assumption.pct_of_revenue
        if pct is None:
            pct = (default_pct or 0) * 100
        return revenue * pct / 100

    elif assumption.method == "fixed":
        base = assumption.fixed_amount or last_value
        escalator = (assumption.annual_escalator_pct or 0) / 100
        # Monthly compounding of annual escalator
        years_elapsed = month_index / 12
        return base * ((1 + escalator) ** years_elapsed)

    elif assumption.method == "headcount":
        hc = assumption.headcount or 0
        cost_per = assumption.loaded_cost_per_head or 0
        return hc * cost_per

    else:
        return last_value


def project_bs_and_cf(
    historical_bs: pd.DataFrame,
    historical_cf: pd.DataFrame | None,
    projected_is: pd.DataFrame,
    assumptions: AssumptionSet,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Project Balance Sheet and Cash Flow together, month by month.

    BS and CF are interdependent — cash comes from CF, which depends on BS changes.
    So we compute them in a single loop.

    Returns (combined_bs_df, combined_cf_df) each with historical + projected rows.
    """
    period_col = "period"

    # Prepare historical BS
    bs = historical_bs.sort_values(period_col).reset_index(drop=True)
    bs["_is_projected"] = False

    # Prepare historical CF
    if historical_cf is not None and not historical_cf.empty:
        cf_hist = historical_cf.sort_values(period_col).reset_index(drop=True)
        cf_hist["_is_projected"] = False
    else:
        cf_hist = pd.DataFrame()

    # Get the projected P&L rows only
    is_projected = projected_is[projected_is["_is_projected"] == True].reset_index(drop=True)
    is_pcol = "period" if "period" in is_projected.columns else "month"

    if is_projected.empty or bs.empty:
        if not bs.empty:
            return bs, cf_hist if not cf_hist.empty else pd.DataFrame()
        return pd.DataFrame(), pd.DataFrame()

    # Last historical BS row as starting point
    last_bs = bs.iloc[-1]

    # Extract carry-forward values
    prev_cash = float(last_bs.get("cash", 0) or 0)
    prev_ar = float(last_bs.get("accounts_receivable", 0) or 0)
    prev_ap = float(last_bs.get("accounts_payable", 0) or 0)
    prev_inventory = float(last_bs.get("inventory", 0) or 0)
    prev_prepaid = float(last_bs.get("prepaid_expenses", 0) or 0)
    prev_other_ca = float(last_bs.get("other_current_assets", 0) or 0)
    prev_ppe = float(last_bs.get("pp_and_e_net", 0) or 0)
    prev_intangibles = float(last_bs.get("intangible_assets", 0) or 0)
    prev_other_nca = float(last_bs.get("other_non_current_assets", 0) or 0)
    prev_accrued = float(last_bs.get("accrued_liabilities", 0) or 0)
    prev_std = float(last_bs.get("short_term_debt", 0) or 0)
    prev_other_cl = float(last_bs.get("other_current_liabilities", 0) or 0)
    prev_ltd = float(last_bs.get("long_term_debt", 0) or 0)
    prev_other_ncl = float(last_bs.get("other_non_current_liabilities", 0) or 0)

    # D&A estimate from historical CF
    monthly_da = 0.0
    if not cf_hist.empty and "depreciation_amortization" in cf_hist.columns:
        da_vals = cf_hist["depreciation_amortization"].dropna()
        if len(da_vals) > 0:
            monthly_da = float(da_vals.mean())

    wc_a = assumptions.working_capital
    debt_a = assumptions.debt
    capex_a = assumptions.capex
    tax_a = assumptions.tax

    bs_rows = []
    cf_rows = []

    for _, is_row in is_projected.iterrows():
        period = str(is_row[is_pcol])
        days = days_in_period(period)
        revenue = float(is_row.get("revenue", 0))
        cogs = float(is_row.get("cogs", 0))
        ebitda = float(is_row.get("ebitda", 0))

        # ── Working Capital from DSO/DPO/DIO ──
        ar = prev_ar
        if wc_a.target_dso is not None and revenue > 0:
            ar = revenue * (wc_a.target_dso / days)

        ap = prev_ap
        if wc_a.target_dpo is not None and cogs > 0:
            ap = cogs * (wc_a.target_dpo / days)

        inventory = prev_inventory
        if wc_a.target_dio is not None and cogs > 0:
            inventory = cogs * (wc_a.target_dio / days)

        # WC change
        wc_change = (ar - prev_ar) + (inventory - prev_inventory) - (ap - prev_ap)

        # ── CapEx ──
        capex = 0.0
        if capex_a.maintenance_pct_of_revenue is not None:
            capex = revenue * capex_a.maintenance_pct_of_revenue / 100
        elif capex_a.maintenance_fixed is not None:
            capex = capex_a.maintenance_fixed
        # Growth capex for this period
        capex += capex_a.growth_capex_by_period.get(period, 0)

        # ── Interest ──
        debt_balance = prev_ltd + prev_std
        interest = debt_balance * (debt_a.interest_rate_annual_pct / 100 / 12)

        # ── Taxes ──
        taxable = ebitda - monthly_da - interest
        taxes = max(0, taxable * (tax_a.effective_tax_rate_pct / 100))

        # ── Cash Flow ──
        net_income = ebitda - monthly_da - interest - taxes
        cfo = net_income + monthly_da - wc_change
        cfi = -capex
        debt_repaid = debt_a.amortization_per_month
        cff = -debt_repaid
        net_cash_change = cfo + cfi + cff
        beginning_cash = prev_cash
        ending_cash = beginning_cash + net_cash_change
        fcf = cfo + cfi

        # ── Update BS ──
        new_ppe = max(0, prev_ppe - monthly_da + capex)
        new_intangibles = max(0, prev_intangibles - monthly_da * 0.1)  # slow amortization
        new_ltd = max(0, prev_ltd - debt_repaid)

        total_ca = ending_cash + ar + inventory + prev_prepaid + prev_other_ca
        total_nca = new_ppe + new_intangibles + prev_other_nca
        total_assets = total_ca + total_nca

        total_cl = ap + prev_accrued + prev_std + prev_other_cl
        total_ncl = new_ltd + prev_other_ncl
        total_liabilities = total_cl + total_ncl

        total_equity = total_assets - total_liabilities
        total_le = total_liabilities + total_equity

        # BS row
        bs_rows.append({
            "period": period,
            "cash": ending_cash,
            "accounts_receivable": ar,
            "inventory": inventory,
            "prepaid_expenses": prev_prepaid,
            "other_current_assets": prev_other_ca,
            "total_current_assets": total_ca,
            "pp_and_e_net": new_ppe,
            "intangible_assets": new_intangibles,
            "other_non_current_assets": prev_other_nca,
            "total_assets": total_assets,
            "accounts_payable": ap,
            "accrued_liabilities": prev_accrued,
            "short_term_debt": prev_std,
            "other_current_liabilities": prev_other_cl,
            "total_current_liabilities": total_cl,
            "long_term_debt": new_ltd,
            "other_non_current_liabilities": prev_other_ncl,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_le,
            "_is_projected": True,
        })

        # CF row
        cf_rows.append({
            "period": period,
            "net_income": net_income,
            "depreciation_amortization": monthly_da,
            "changes_in_working_capital": -wc_change,
            "other_operating": 0,
            "cash_from_operations": cfo,
            "capex": -capex,
            "acquisitions": 0,
            "other_investing": 0,
            "cash_from_investing": cfi,
            "debt_issued": 0,
            "debt_repaid": -debt_repaid,
            "equity_issued": 0,
            "dividends_paid": 0,
            "other_financing": 0,
            "cash_from_financing": cff,
            "net_change_in_cash": net_cash_change,
            "beginning_cash": beginning_cash,
            "ending_cash": ending_cash,
            "free_cash_flow": fcf,
            "_is_projected": True,
        })

        # Update carry-forward for next month
        prev_cash = ending_cash
        prev_ar = ar
        prev_ap = ap
        prev_inventory = inventory
        prev_ppe = new_ppe
        prev_intangibles = new_intangibles
        prev_ltd = new_ltd

    # Combine historical + projected
    projected_bs = pd.DataFrame(bs_rows)
    combined_bs = pd.concat([bs, projected_bs], ignore_index=True)

    if not cf_hist.empty:
        projected_cf = pd.DataFrame(cf_rows)
        combined_cf = pd.concat([cf_hist, projected_cf], ignore_index=True)
    else:
        combined_cf = pd.DataFrame(cf_rows)
        if not combined_cf.empty:
            combined_cf["_is_projected"] = True

    return combined_bs, combined_cf


def _next_period(period_str: str) -> str:
    """Increment a YYYY-MM period by one month."""
    parts = period_str.split("-")
    year = int(parts[0])
    month = int(parts[1])
    month += 1
    if month > 12:
        month = 1
        year += 1
    return f"{year}-{month:02d}"
