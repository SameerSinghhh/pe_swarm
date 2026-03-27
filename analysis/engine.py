"""
Analysis engine orchestrator.

Takes a dict of NormalizedResult objects (keyed by doc_type) and runs
all applicable analysis modules. Gracefully skips modules when required
data is missing.
"""

import pandas as pd

from core.result import NormalizedResult
from analysis.types import AnalysisResult
from analysis.ebitda_bridge import compute_ebitda_bridges
from analysis.variance import compute_variance
from analysis.margins import compute_margins
from analysis.working_capital import compute_working_capital
from analysis.fcf import compute_fcf
from analysis.revenue_analytics import compute_revenue_analytics
from analysis.trends import detect_trends
from analysis.utils import get_period_col


def run_analysis(
    results: dict[str, NormalizedResult],
    current_period: str | None = None,
) -> AnalysisResult:
    """
    Run all applicable analysis modules on the provided data.

    Input: dict keyed by doc_type (e.g., "income_statement", "balance_sheet").
           Each value is a NormalizedResult from the ingestion pipeline.
    Output: AnalysisResult with all sub-results.

    Modules are skipped gracefully when required data is missing.
    """
    modules_run = []
    warnings = []

    # Extract DataFrames
    income_df = _get_df(results, "income_statement")
    balance_sheet_df = _get_df(results, "balance_sheet")
    cash_flow_df = _get_df(results, "cash_flow")
    working_capital_df = _get_df(results, "working_capital")
    revenue_detail_df = _get_df(results, "revenue_detail")
    kpi_df = _get_df(results, "kpi_operational")

    # Determine current period from income statement
    if current_period is None and income_df is not None:
        pcol = get_period_col(income_df)
        if pcol in income_df.columns:
            current_period = str(income_df.sort_values(pcol).iloc[-1][pcol])

    # ── Module 1: EBITDA Bridge ──
    ebitda_bridges = None
    if income_df is not None:
        try:
            ebitda_bridges = compute_ebitda_bridges(income_df, current_period)
            modules_run.append("ebitda_bridge")
        except Exception as e:
            warnings.append(f"EBITDA Bridge failed: {e}")

    # ── Module 2: Variance Analysis ──
    variance = None
    if income_df is not None:
        try:
            variance = compute_variance(income_df)
            modules_run.append("variance")
        except Exception as e:
            warnings.append(f"Variance Analysis failed: {e}")

    # ── Module 3: Margins & Growth ──
    margins = None
    if income_df is not None:
        try:
            margins = compute_margins(income_df)
            modules_run.append("margins")
        except Exception as e:
            warnings.append(f"Margins failed: {e}")

    # ── Module 4: Working Capital ──
    wc = None
    if working_capital_df is not None or (balance_sheet_df is not None and income_df is not None):
        try:
            wc = compute_working_capital(balance_sheet_df, income_df, working_capital_df)
            modules_run.append("working_capital")
        except Exception as e:
            warnings.append(f"Working Capital failed: {e}")

    # ── Module 5: FCF ──
    fcf_result = None
    if cash_flow_df is not None:
        try:
            fcf_result = compute_fcf(cash_flow_df, income_df, balance_sheet_df)
            modules_run.append("fcf")
        except Exception as e:
            warnings.append(f"FCF failed: {e}")

    # ── Module 6: Revenue Analytics ──
    rev_analytics = None
    if revenue_detail_df is not None or kpi_df is not None:
        try:
            rev_analytics = compute_revenue_analytics(revenue_detail_df, kpi_df)
            modules_run.append("revenue_analytics")
        except Exception as e:
            warnings.append(f"Revenue Analytics failed: {e}")

    # ── Module 7: Trend Detection ──
    trend_result = None
    try:
        all_metrics = _collect_metrics(margins, wc, fcf_result, rev_analytics)
        if all_metrics:
            trend_result = detect_trends(all_metrics)
            modules_run.append("trends")
    except Exception as e:
        warnings.append(f"Trend Detection failed: {e}")

    return AnalysisResult(
        ebitda_bridges=ebitda_bridges,
        variance=variance,
        margins=margins,
        working_capital=wc,
        fcf=fcf_result,
        revenue_analytics=rev_analytics,
        trends=trend_result,
        modules_run=modules_run,
        warnings=warnings,
    )


def _get_df(results: dict[str, NormalizedResult], doc_type: str) -> pd.DataFrame | None:
    """Extract DataFrame from results dict by doc_type."""
    if doc_type in results:
        return results[doc_type].df
    return None


def _collect_metrics(margins, wc, fcf_result, rev_analytics) -> dict[str, list[tuple[str, float]]]:
    """Collect all metric time series from analysis results for trend detection."""
    metrics: dict[str, list[tuple[str, float]]] = {}

    # From margins
    if margins and margins.periods:
        for attr in [
            "gross_margin_pct", "ebitda_margin_pct", "sm_pct_revenue",
            "rd_pct_revenue", "ga_pct_revenue", "opex_pct_revenue",
            "revenue_growth_mom", "ebitda_growth_mom",
        ]:
            series = []
            for p in margins.periods:
                val = getattr(p, attr, None)
                if val is not None:
                    series.append((p.period, val))
            if series:
                metrics[attr] = series

    # From working capital
    if wc and wc.periods:
        for attr in ["dso", "dpo", "dio", "ccc"]:
            series = []
            for p in wc.periods:
                val = getattr(p, attr, None)
                if val is not None:
                    series.append((p.period, val))
            if series:
                metrics[attr] = series

    # From FCF
    if fcf_result and fcf_result.periods:
        for attr in ["free_cash_flow", "cash_conversion_ratio", "net_debt_to_ltm_ebitda"]:
            series = []
            for p in fcf_result.periods:
                val = getattr(p, attr, None)
                if val is not None:
                    series.append((p.period, val))
            if series:
                metrics[attr] = series

    # From revenue analytics KPI trends
    if rev_analytics and rev_analytics.kpi_trends:
        for metric_name, series in rev_analytics.kpi_trends.items():
            metrics[metric_name] = series

    return metrics
