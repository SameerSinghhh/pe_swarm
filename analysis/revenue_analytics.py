"""
Module 6: Revenue Analytics.

Computes:
  - Revenue concentration (top 1/5/10 %, Herfindahl index)
  - Price/volume/mix decomposition
  - KPI trends (NRR, churn, CAC, LTV)
"""

import pandas as pd

from analysis.types import (
    ConcentrationMetrics, PriceVolumeDecomp,
    RevenueAnalyticsResult,
)
from analysis.utils import safe_pct, get_value, has_column


def compute_revenue_analytics(
    revenue_detail_df: pd.DataFrame | None = None,
    kpi_df: pd.DataFrame | None = None,
) -> RevenueAnalyticsResult:
    """
    Compute revenue analytics from revenue detail and KPI data.

    Input: Revenue detail DataFrame (by customer/product) and/or KPI DataFrame.
    Output: RevenueAnalyticsResult with concentration, price/volume, and KPI trends.
    """
    concentration = []
    price_volume = []
    kpi_trends: dict[str, list[tuple[str, float]]] = {}

    if revenue_detail_df is not None and "period" in revenue_detail_df.columns:
        # Determine which dimension to use for concentration
        for dim in ["customer", "product", "segment"]:
            if has_column(revenue_detail_df, dim):
                concentration = _compute_concentration(revenue_detail_df, dim)
                break

        # Price/volume decomposition (requires units_sold + unit_price + product)
        if (has_column(revenue_detail_df, "units_sold") and
            has_column(revenue_detail_df, "unit_price") and
            has_column(revenue_detail_df, "product")):
            price_volume = _compute_price_volume(revenue_detail_df)

    if kpi_df is not None and "period" in kpi_df.columns:
        kpi_trends = _extract_kpi_trends(kpi_df)

    return RevenueAnalyticsResult(
        concentration=concentration,
        price_volume=price_volume,
        kpi_trends=kpi_trends,
    )


def _compute_concentration(
    df: pd.DataFrame,
    dimension: str,
) -> list[ConcentrationMetrics]:
    """Compute revenue concentration by a given dimension, per period."""
    results = []

    for period, group in df.groupby("period"):
        rev_by_dim = group.groupby(dimension)["revenue"].sum().sort_values(ascending=False)
        total = rev_by_dim.sum()

        if total == 0:
            continue

        n = len(rev_by_dim)
        shares = rev_by_dim / total

        top1_pct = safe_pct(rev_by_dim.iloc[0], total) if n >= 1 else None
        top5_pct = safe_pct(rev_by_dim.iloc[:5].sum(), total) if n >= 1 else None
        top10_pct = safe_pct(rev_by_dim.iloc[:10].sum(), total) if n >= 1 else None

        # Herfindahl index: sum of squared shares (0 to 1)
        herfindahl = float((shares ** 2).sum())

        results.append(ConcentrationMetrics(
            period=str(period),
            dimension=dimension,
            top1_pct=top1_pct,
            top5_pct=top5_pct,
            top10_pct=top10_pct,
            herfindahl=round(herfindahl, 4),
            count=n,
        ))

    return results


def _compute_price_volume(df: pd.DataFrame) -> list[PriceVolumeDecomp]:
    """
    Compute price/volume/mix decomposition.

    For each product p:
      price_effect_p  = current_units_p * (current_price_p - prior_price_p)
      volume_effect_p = (current_units_p - prior_units_p) * prior_price_p

    Mix effect = total_change - price_effect - volume_effect

    Verification: price + volume + mix == total_change
    """
    results = []
    periods = sorted(df["period"].unique())

    for i in range(1, len(periods)):
        current_period = periods[i]
        prior_period = periods[i - 1]

        current_data = df[df["period"] == current_period]
        prior_data = df[df["period"] == prior_period]

        # Get products present in both periods
        current_products = set(current_data["product"])
        prior_products = set(prior_data["product"])
        common_products = current_products & prior_products

        total_current_revenue = current_data["revenue"].sum()
        total_prior_revenue = prior_data["revenue"].sum()
        total_change = total_current_revenue - total_prior_revenue

        price_effect = 0.0
        volume_effect = 0.0

        for product in common_products:
            cur = current_data[current_data["product"] == product].iloc[0]
            pri = prior_data[prior_data["product"] == product].iloc[0]

            cur_units = get_value(cur, "units_sold")
            cur_price = get_value(cur, "unit_price")
            pri_units = get_value(pri, "units_sold")
            pri_price = get_value(pri, "unit_price")

            # Price effect: same volume, different price
            price_effect += cur_units * (cur_price - pri_price)
            # Volume effect: same price, different volume
            volume_effect += (cur_units - pri_units) * pri_price

        # Mix effect: residual (captures new/lost products + interaction)
        mix_effect = total_change - price_effect - volume_effect

        verification_delta = abs(price_effect + volume_effect + mix_effect - total_change)

        results.append(PriceVolumeDecomp(
            period=str(current_period),
            price_effect=round(price_effect, 2),
            volume_effect=round(volume_effect, 2),
            mix_effect=round(mix_effect, 2),
            total_change=round(total_change, 2),
            verification_delta=verification_delta,
            is_verified=verification_delta < 0.01,
        ))

    return results


def _extract_kpi_trends(kpi_df: pd.DataFrame) -> dict[str, list[tuple[str, float]]]:
    """Extract time series of key KPI metrics."""
    kpi_columns = [
        "net_revenue_retention", "monthly_churn_rate", "cac", "ltv",
        "ltv_cac_ratio", "total_headcount", "nps_score",
        "gross_revenue_retention", "capacity_utilization",
    ]

    trends: dict[str, list[tuple[str, float]]] = {}
    df = kpi_df.sort_values("period")

    for col in kpi_columns:
        if has_column(df, col):
            series = []
            for _, row in df.iterrows():
                val = get_value(row, col, default=None)
                if val is not None:
                    series.append((str(row["period"]), val))
            if series:
                trends[col] = series

    return trends
