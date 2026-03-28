"""
Initiative application logic.

Each initiative modifies projected EBITDA with ramp, confidence weighting,
and one-time implementation cost.
"""

from modeling.types import Initiative


def apply_initiatives(
    base_ebitda: float,
    period: str,
    initiatives: list[Initiative],
) -> tuple[float, float]:
    """
    Apply all enabled initiatives to base EBITDA for the given period.

    Returns (adjusted_ebitda, total_implementation_cost_this_period).

    Ramp logic: linear over ramp_months.
      Month 1 of a 3-month ramp: 1/3 of run-rate
      Month 2: 2/3
      Month 3+: full run-rate

    Confidence: impact × (confidence_pct / 100)
    Toggle: enabled=False → zero impact
    """
    total_uplift = 0.0
    total_impl_cost = 0.0

    for init in initiatives:
        if not init.enabled:
            continue

        if not init.start_period or period < init.start_period:
            continue

        # Calculate months since start
        months_since = _months_between(init.start_period, period)

        # Ramp factor
        ramp_months = max(1, init.ramp_months)
        ramp_factor = min(1.0, (months_since + 1) / ramp_months)

        # EBITDA uplift
        uplift = init.ebitda_impact_run_rate * ramp_factor * (init.confidence_pct / 100)
        total_uplift += uplift

        # Implementation cost: only in the start month
        if period == init.start_period:
            total_impl_cost += init.implementation_cost

    return base_ebitda + total_uplift, total_impl_cost


def _months_between(start: str, end: str) -> int:
    """Calculate months between two YYYY-MM periods."""
    try:
        s_parts = start.split("-")
        e_parts = end.split("-")
        s_year, s_month = int(s_parts[0]), int(s_parts[1])
        e_year, e_month = int(e_parts[0]), int(e_parts[1])
        return (e_year - s_year) * 12 + (e_month - s_month)
    except (ValueError, IndexError):
        return 0
