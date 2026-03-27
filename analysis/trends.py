"""
Module 7: Trend Detection.

Scans all metric time series and automatically flags:
  1. Consecutive decline (3+ periods declining → warning, 5+ → critical)
  2. Margin compression (>200bps single-period drop)
  3. Anomaly (>2σ from trailing mean → warning, >3σ → critical)
  4. Acceleration change (growth rate declining for 2+ periods)
"""

import math
from analysis.types import TrendFlag, TrendResult, FlagType, Severity


def detect_trends(
    metrics: dict[str, list[tuple[str, float]]],
    consecutive_n_warn: int = 3,
    consecutive_n_crit: int = 5,
    margin_compression_bps: float = 200,
    anomaly_sigma_warn: float = 2.0,
    anomaly_sigma_crit: float = 3.0,
    trailing_window: int = 6,
) -> TrendResult:
    """
    Scan all metric time series for flags.

    Input: dict of metric_name → list of (period, value) sorted chronologically.
    Output: TrendResult with list of TrendFlag.

    All parameters have sensible defaults. Override for custom sensitivity.
    """
    flags: list[TrendFlag] = []

    for metric_name, series in metrics.items():
        if len(series) < 2:
            continue

        values = [v for _, v in series]
        periods = [p for p, _ in series]

        # 1. Consecutive decline
        _check_consecutive_decline(
            metric_name, values, periods, flags,
            n_warn=consecutive_n_warn, n_crit=consecutive_n_crit,
        )

        # 2. Margin compression (only for _pct metrics)
        if "_pct" in metric_name or "margin" in metric_name.lower():
            _check_margin_compression(
                metric_name, values, periods, flags,
                threshold_bps=margin_compression_bps,
            )

        # 3. Anomaly detection
        if len(values) >= trailing_window + 1:
            _check_anomaly(
                metric_name, values, periods, flags,
                window=trailing_window,
                sigma_warn=anomaly_sigma_warn,
                sigma_crit=anomaly_sigma_crit,
            )

        # 4. Acceleration change (growth rate declining)
        if len(values) >= 4:
            _check_acceleration(metric_name, values, periods, flags)

    return TrendResult(flags=flags)


def _check_consecutive_decline(
    metric: str, values: list[float], periods: list[str],
    flags: list[TrendFlag], n_warn: int, n_crit: int,
):
    """Flag if the last N values are strictly declining."""
    n = len(values)
    if n < n_warn:
        return

    # Count how many consecutive declining periods at the end
    decline_count = 0
    for i in range(n - 1, 0, -1):
        if values[i] < values[i - 1]:
            decline_count += 1
        else:
            break

    if decline_count >= n_crit:
        flags.append(TrendFlag(
            metric=metric,
            flag_type=FlagType.CONSECUTIVE_DECLINE,
            severity=Severity.CRITICAL,
            current_value=values[-1],
            period=periods[-1],
            detail=f"{metric} has declined for {decline_count} consecutive periods",
        ))
    elif decline_count >= n_warn:
        flags.append(TrendFlag(
            metric=metric,
            flag_type=FlagType.CONSECUTIVE_DECLINE,
            severity=Severity.WARNING,
            current_value=values[-1],
            period=periods[-1],
            detail=f"{metric} has declined for {decline_count} consecutive periods",
        ))


def _check_margin_compression(
    metric: str, values: list[float], periods: list[str],
    flags: list[TrendFlag], threshold_bps: float,
):
    """Flag single-period margin drop exceeding threshold (in basis points)."""
    for i in range(1, len(values)):
        drop_bps = (values[i - 1] - values[i]) * 100  # convert pct points to bps
        if drop_bps > threshold_bps:
            flags.append(TrendFlag(
                metric=metric,
                flag_type=FlagType.MARGIN_COMPRESSION,
                severity=Severity.WARNING,
                current_value=values[i],
                period=periods[i],
                detail=f"{metric} compressed {drop_bps:.0f}bps in {periods[i]} (from {values[i-1]:.1f}% to {values[i]:.1f}%)",
            ))


def _check_anomaly(
    metric: str, values: list[float], periods: list[str],
    flags: list[TrendFlag], window: int,
    sigma_warn: float, sigma_crit: float,
):
    """Flag if latest value is >N standard deviations from trailing mean."""
    latest = values[-1]
    trailing = values[-(window + 1):-1]  # exclude the latest value

    if len(trailing) < 3:
        return

    mean = sum(trailing) / len(trailing)
    variance = sum((x - mean) ** 2 for x in trailing) / len(trailing)
    std = math.sqrt(variance)

    if std == 0:
        return

    z_score = abs(latest - mean) / std

    if z_score > sigma_crit:
        direction = "above" if latest > mean else "below"
        flags.append(TrendFlag(
            metric=metric,
            flag_type=FlagType.ANOMALY,
            severity=Severity.CRITICAL,
            current_value=latest,
            period=periods[-1],
            detail=f"{metric} is {z_score:.1f}σ {direction} trailing {window}-period mean ({mean:.1f})",
        ))
    elif z_score > sigma_warn:
        direction = "above" if latest > mean else "below"
        flags.append(TrendFlag(
            metric=metric,
            flag_type=FlagType.ANOMALY,
            severity=Severity.WARNING,
            current_value=latest,
            period=periods[-1],
            detail=f"{metric} is {z_score:.1f}σ {direction} trailing {window}-period mean ({mean:.1f})",
        ))


def _check_acceleration(
    metric: str, values: list[float], periods: list[str],
    flags: list[TrendFlag],
):
    """Flag if the growth rate itself has declined for 2+ consecutive periods."""
    if len(values) < 4:
        return

    # Compute period-over-period changes
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]

    # Check if last 2+ changes are decreasing (deceleration)
    decel_count = 0
    for i in range(len(changes) - 1, 0, -1):
        if changes[i] < changes[i - 1]:
            decel_count += 1
        else:
            break

    if decel_count >= 2:
        flags.append(TrendFlag(
            metric=metric,
            flag_type=FlagType.ACCELERATION_CHANGE,
            severity=Severity.INFO,
            current_value=values[-1],
            period=periods[-1],
            detail=f"{metric} growth rate has decelerated for {decel_count} consecutive periods",
        ))
