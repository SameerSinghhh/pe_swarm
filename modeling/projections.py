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
