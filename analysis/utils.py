"""
Shared utility functions for the analysis engine.

All division operations go through safe_div/safe_pct to prevent
ZeroDivisionError. All period lookups use consistent date handling.
"""

import calendar
import math
from typing import Optional

import pandas as pd

from analysis.types import Favorability


def safe_div(numerator, denominator) -> Optional[float]:
    """Safe division. Returns None if either value is None, 0 denom, NaN, or inf."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    try:
        n = float(numerator)
        d = float(denominator)
    except (TypeError, ValueError):
        return None
    if math.isnan(n) or math.isinf(n) or math.isnan(d) or math.isinf(d):
        return None
    return n / d


def safe_pct(numerator: float, denominator: float) -> Optional[float]:
    """Safe percentage. Returns None if denominator is 0, NaN, or None."""
    result = safe_div(numerator, denominator)
    if result is None:
        return None
    return result * 100


def days_in_period(period_str: str) -> int:
    """Return the number of days in a YYYY-MM period."""
    try:
        parts = period_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
        return calendar.monthrange(year, month)[1]
    except (ValueError, IndexError, TypeError):
        return 30  # safe fallback


def get_prior_year_period(period_str: str) -> str:
    """Return the period exactly 12 months prior. '2026-03' → '2025-03'."""
    try:
        parts = period_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
        return f"{year - 1}-{month:02d}"
    except (ValueError, IndexError, TypeError):
        return ""


def has_column(df: pd.DataFrame, col: str) -> bool:
    """True if column exists in DataFrame and has at least one non-null value."""
    if col not in df.columns:
        return False
    return df[col].notna().any()


def get_value(row: pd.Series, col: str, default: float = 0.0) -> float:
    """Safely get a numeric value from a row, returning default if missing/NaN."""
    if col not in row.index:
        return default
    val = row[col]
    if pd.isna(val):
        return default
    return float(val)


def find_period_row(df: pd.DataFrame, period: str, period_col: str = "period") -> pd.Series | None:
    """Find the row matching a specific period. Returns None if not found."""
    if period_col not in df.columns:
        return None
    mask = df[period_col] == period
    if mask.sum() == 0:
        return None
    return df.loc[mask].iloc[0]


def get_period_col(df: pd.DataFrame) -> str:
    """Determine the period column name ('period' or 'month')."""
    if "period" in df.columns:
        return "period"
    if "month" in df.columns:
        return "month"
    return "period"


# Cost items: an increase is UNFAVORABLE (hurts EBITDA)
# Revenue/profit items: an increase is FAVORABLE (helps EBITDA)
COST_ITEMS = {"cogs", "sales_marketing", "rd", "ga", "total_opex"}
PROFIT_ITEMS = {"revenue", "gross_profit", "ebitda"}


def favorability(line_item: str, dollar_change: float) -> Favorability:
    """Determine if a change is favorable or unfavorable."""
    if dollar_change == 0:
        return Favorability.NEUTRAL

    if line_item in COST_ITEMS:
        # Costs going UP is bad
        return Favorability.UNFAVORABLE if dollar_change > 0 else Favorability.FAVORABLE
    elif line_item in PROFIT_ITEMS:
        # Revenue/profit going UP is good
        return Favorability.FAVORABLE if dollar_change > 0 else Favorability.UNFAVORABLE
    else:
        return Favorability.NEUTRAL
