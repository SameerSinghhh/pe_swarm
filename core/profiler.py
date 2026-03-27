"""
Data profiling — before and after normalization.

profile_raw(): Analyzes raw data to feed better context into AI normalization.
profile_normalized(): Generates quality scores for the clean output.
"""

from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from core.schemas.base import DocumentSchema
from core.cleaning import to_numeric, parse_period


# ── Dataclasses ──

@dataclass
class ColumnProfile:
    name: str
    inferred_type: str  # "numeric", "date", "text", "mixed"
    null_count: int
    null_pct: float
    unique_count: int
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    sample_values: list[str] = field(default_factory=list)


@dataclass
class TemporalProfile:
    field_name: str
    period_count: int
    min_period: str | None = None
    max_period: str | None = None
    gaps: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)


@dataclass
class AnomalyReport:
    all_zero_rows: list[int] = field(default_factory=list)
    all_nan_rows: list[int] = field(default_factory=list)
    sudden_changes: list[dict] = field(default_factory=list)


@dataclass
class DataProfile:
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    temporal: TemporalProfile | None = None
    anomalies: AnomalyReport = field(default_factory=AnomalyReport)
    row_count: int = 0
    col_count: int = 0


@dataclass
class QualityReport:
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    coverage_score: float = 0.0
    reasonableness_score: float = 0.0
    quality_score: float = 0.0
    details: dict = field(default_factory=dict)


# ── Raw profiling (before normalization) ──

def profile_raw(df: pd.DataFrame, schema: DocumentSchema) -> DataProfile:
    """Profile raw data before normalization."""
    profile = DataProfile(row_count=len(df), col_count=len(df.columns))

    for col in df.columns:
        cp = _profile_column(df[col], str(col))
        profile.column_profiles.append(cp)

    # Detect temporal column
    profile.temporal = _detect_temporal(df)

    # Detect anomalies
    profile.anomalies = _detect_anomalies(df)

    return profile


def _profile_column(series: pd.Series, name: str) -> ColumnProfile:
    """Profile a single column."""
    null_count = int(series.isna().sum())
    null_pct = null_count / len(series) * 100 if len(series) > 0 else 0
    unique_count = int(series.nunique())

    # Type inference
    non_null = series.dropna()
    if len(non_null) == 0:
        inferred_type = "empty"
    else:
        numeric = pd.to_numeric(non_null.astype(str).str.replace(r"[$,()]", "", regex=True), errors="coerce")
        numeric_pct = numeric.notna().mean()
        if numeric_pct > 0.7:
            inferred_type = "numeric"
        else:
            # Try date parsing
            date_success = non_null.astype(str).apply(lambda v: parse_period(v) is not None).mean()
            if date_success > 0.5:
                inferred_type = "date"
            elif numeric_pct > 0.3:
                inferred_type = "mixed"
            else:
                inferred_type = "text"

    # Stats for numeric columns
    min_val = max_val = mean_val = None
    if inferred_type == "numeric" and len(non_null) > 0:
        cleaned = to_numeric(non_null)
        cleaned = cleaned.dropna()
        if len(cleaned) > 0:
            min_val = float(cleaned.min())
            max_val = float(cleaned.max())
            mean_val = float(cleaned.mean())

    sample_values = [str(v) for v in non_null.unique()[:5]]

    return ColumnProfile(
        name=name,
        inferred_type=inferred_type,
        null_count=null_count,
        null_pct=round(null_pct, 1),
        unique_count=unique_count,
        min_val=min_val,
        max_val=max_val,
        mean_val=mean_val,
        sample_values=sample_values,
    )


def _detect_temporal(df: pd.DataFrame) -> TemporalProfile | None:
    """Find the most likely temporal column and profile it."""
    best_col = None
    best_success = 0

    for col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        success = non_null.astype(str).apply(lambda v: parse_period(v) is not None).mean()
        if success > best_success:
            best_success = success
            best_col = col

    if best_col is None or best_success < 0.3:
        return None

    parsed = df[best_col].astype(str).apply(parse_period).dropna()
    periods = sorted(parsed.unique())

    # Detect gaps
    gaps = []
    duplicates = []
    if len(periods) >= 2:
        try:
            dates = pd.to_datetime([p + "-01" for p in periods])
            expected = pd.date_range(dates.min(), dates.max(), freq="MS")
            expected_strs = set(d.strftime("%Y-%m") for d in expected)
            actual_strs = set(periods)
            gaps = sorted(expected_strs - actual_strs)
        except Exception:
            pass

    # Detect duplicate periods
    all_parsed = df[best_col].astype(str).apply(parse_period).dropna()
    dupe_mask = all_parsed.duplicated(keep=False)
    if dupe_mask.any():
        duplicates = sorted(all_parsed[dupe_mask].unique())

    return TemporalProfile(
        field_name=str(best_col),
        period_count=len(periods),
        min_period=periods[0] if periods else None,
        max_period=periods[-1] if periods else None,
        gaps=gaps,
        duplicates=duplicates,
    )


def _detect_anomalies(df: pd.DataFrame) -> AnomalyReport:
    """Detect anomalous rows in the data."""
    report = AnomalyReport()

    # Find numeric-looking columns
    numeric_cols = []
    for col in df.columns:
        series = pd.to_numeric(
            df[col].astype(str).str.replace(r"[$,()]", "", regex=True),
            errors="coerce",
        )
        if series.notna().mean() > 0.5:
            numeric_cols.append(col)

    if not numeric_cols:
        return report

    numeric_df = df[numeric_cols].apply(
        lambda s: pd.to_numeric(s.astype(str).str.replace(r"[$,()]", "", regex=True), errors="coerce")
    )

    # All-zero rows
    zero_mask = (numeric_df == 0).all(axis=1)
    report.all_zero_rows = zero_mask[zero_mask].index.tolist()

    # All-NaN rows
    nan_mask = numeric_df.isna().all(axis=1)
    report.all_nan_rows = nan_mask[nan_mask].index.tolist()

    # Sudden changes (>200% MoM)
    for col in numeric_cols[:5]:  # limit to first 5 numeric columns
        series = numeric_df[col].dropna()
        if len(series) < 2:
            continue
        pct = series.pct_change().abs()
        spikes = pct[pct > 2.0]
        for idx in spikes.index:
            report.sudden_changes.append({
                "column": str(col),
                "row": int(idx),
                "pct_change": round(float(pct[idx]) * 100, 1),
            })

    return report


# ── Prompt formatting ──

def format_profile_for_prompt(profile: DataProfile) -> str:
    """Render a DataProfile as text to inject into the AI normalization prompt."""
    lines = ["DATA PROFILE:", f"  Rows: {profile.row_count}, Columns: {profile.col_count}"]

    for cp in profile.column_profiles:
        range_str = ""
        if cp.min_val is not None and cp.max_val is not None:
            if abs(cp.max_val) >= 1_000_000:
                range_str = f", range ${cp.min_val/1e6:.1f}M–${cp.max_val/1e6:.1f}M"
            elif abs(cp.max_val) >= 1_000:
                range_str = f", range ${cp.min_val:,.0f}–${cp.max_val:,.0f}"
        null_str = f", {cp.null_pct:.0f}% null" if cp.null_pct > 0 else ""
        lines.append(f"  {cp.name}: {cp.inferred_type}, {cp.unique_count} unique{null_str}{range_str}")

    if profile.temporal:
        t = profile.temporal
        lines.append(f"  Temporal: {t.field_name}, {t.period_count} periods ({t.min_period} to {t.max_period})")
        if t.gaps:
            lines.append(f"  Gaps: {t.gaps}")
        if t.duplicates:
            lines.append(f"  Duplicate periods: {t.duplicates}")

    a = profile.anomalies
    if a.all_zero_rows:
        lines.append(f"  Anomaly: {len(a.all_zero_rows)} all-zero rows")
    if a.all_nan_rows:
        lines.append(f"  Anomaly: {len(a.all_nan_rows)} all-NaN rows")
    if a.sudden_changes:
        lines.append(f"  Anomaly: {len(a.sudden_changes)} sudden value changes (>200%)")

    return "\n".join(lines)


# ── Normalized output profiling ──

def profile_normalized(
    df: pd.DataFrame,
    schema: DocumentSchema,
    audit_trail: list[dict],
) -> QualityReport:
    """Profile normalized data and produce quality scores."""

    details = {}

    # ── Completeness (30%) ──
    required_fields = [f for f in schema.required_fields if f in df.columns]
    total_required_cells = len(df) * len(required_fields) if required_fields else 1
    null_required_cells = sum(df[f].isna().sum() for f in required_fields)
    completeness = max(0, (1 - null_required_cells / total_required_cells) * 100)

    # Penalize auto-filled zeros
    zero_fills = sum(1 for e in audit_trail if e.get("action") == "auto_fill_zero")
    if zero_fills > 0:
        completeness = max(0, completeness - zero_fills * 5)

    details["completeness"] = {
        "score": round(completeness, 1),
        "null_cells": int(null_required_cells),
        "total_cells": total_required_cells,
        "zero_fills": zero_fills,
    }

    # ── Consistency (25%) ──
    consistency_checks = 0
    consistency_passes = 0
    for deriv in schema.derivations:
        if deriv.target in df.columns:
            deps_present = all(d in df.columns for d in deriv.dependencies)
            if deps_present:
                consistency_checks += len(df)
                try:
                    expected = df.apply(deriv.formula, axis=1)
                    actual = df[deriv.target]
                    close = ((actual - expected).abs() < max(1.0, actual.abs().mean() * 0.02))
                    consistency_passes += int(close.sum())
                except Exception:
                    pass

    consistency = (consistency_passes / consistency_checks * 100) if consistency_checks > 0 else 100
    details["consistency"] = {
        "score": round(consistency, 1),
        "checks": consistency_checks,
        "passes": consistency_passes,
    }

    # ── Coverage (25%) ──
    temporal = schema.temporal_field
    coverage = 100.0
    if temporal in df.columns:
        try:
            dates = pd.to_datetime(df[temporal], format="%Y-%m", errors="coerce").dropna()
            if len(dates) >= 2:
                expected_range = pd.date_range(dates.min(), dates.max(), freq="MS")
                coverage = min(100, len(dates) / len(expected_range) * 100)
        except Exception:
            pass

    details["coverage"] = {
        "score": round(coverage, 1),
        "periods": len(df),
    }

    # ── Reasonableness (20%) ──
    reasonable_checks = 0
    reasonable_passes = 0

    if "revenue" in df.columns:
        reasonable_checks += len(df)
        reasonable_passes += int((df["revenue"] >= 0).sum())

    if "revenue" in df.columns and "gross_profit" in df.columns:
        mask = df["revenue"] != 0
        if mask.any():
            margin = df.loc[mask, "gross_profit"] / df.loc[mask, "revenue"] * 100
            reasonable_checks += len(margin)
            reasonable_passes += int(((margin >= -50) & (margin <= 100)).sum())

    if "revenue" in df.columns and "ebitda" in df.columns:
        mask = df["revenue"] != 0
        if mask.any():
            margin = df.loc[mask, "ebitda"] / df.loc[mask, "revenue"] * 100
            reasonable_checks += len(margin)
            reasonable_passes += int(((margin >= -100) & (margin <= 100)).sum())

    reasonableness = (reasonable_passes / reasonable_checks * 100) if reasonable_checks > 0 else 100
    details["reasonableness"] = {
        "score": round(reasonableness, 1),
        "checks": reasonable_checks,
        "passes": reasonable_passes,
    }

    # ── Weighted quality score ──
    quality_score = (
        completeness * 0.30 +
        consistency * 0.25 +
        coverage * 0.25 +
        reasonableness * 0.20
    )

    return QualityReport(
        completeness_score=round(completeness, 1),
        consistency_score=round(consistency, 1),
        coverage_score=round(coverage, 1),
        reasonableness_score=round(reasonableness, 1),
        quality_score=round(quality_score, 1),
        details=details,
    )
