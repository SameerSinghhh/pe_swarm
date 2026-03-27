"""
Validation engine. Runs structural, accounting, and reasonableness checks.
Tracks auto-corrections in the audit trail.
"""

from dataclasses import dataclass, field
import pandas as pd
from core.schemas.base import DocumentSchema


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[str] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)


def validate(
    df: pd.DataFrame,
    schema: DocumentSchema,
    audit_trail: list[dict] | None = None,
) -> ValidationResult:
    """
    Comprehensive validation of normalized data.
    Returns ValidationResult with issues and auto-corrections.
    """
    if audit_trail is None:
        audit_trail = []

    issues = []
    corrections = []

    # ── Structural checks ──

    # Required columns
    for fname in schema.required_fields:
        if fname not in df.columns:
            issues.append(f"ERROR: Missing required column: {fname}")

    if _has_errors(issues):
        return ValidationResult(is_valid=False, issues=issues, corrections=corrections)

    # Minimum rows
    min_rows = getattr(schema, 'min_rows', 1)
    if len(df) < min_rows:
        issues.append(f"ERROR: Need at least {min_rows} rows, got {len(df)}")
        return ValidationResult(is_valid=False, issues=issues, corrections=corrections)

    # Financial columns are numeric
    for fname in schema.financial_fields:
        if fname in df.columns and not pd.api.types.is_numeric_dtype(df[fname]):
            issues.append(f"ERROR: Column '{fname}' is not numeric")

    if _has_errors(issues):
        return ValidationResult(is_valid=False, issues=issues, corrections=corrections)

    # ── Temporal checks ──

    temporal = schema.temporal_field
    if temporal in df.columns:
        # Duplicates (skip for detail-level schemas where multiple rows per period is expected)
        if not schema.allows_duplicate_periods:
            dupes = df[temporal].duplicated()
            if dupes.any():
                dupe_vals = df.loc[dupes, temporal].unique().tolist()
                issues.append(f"Warning: Duplicate periods: {dupe_vals}")

        # Chronological order
        try:
            dates = pd.to_datetime(df[temporal], format="%Y-%m", errors="coerce")
            if dates.notna().all() and not dates.is_monotonic_increasing:
                # Auto-sort
                df.sort_values(temporal, inplace=True)
                df.reset_index(drop=True, inplace=True)
                correction = {
                    "action": "auto_sorted",
                    "field": temporal,
                    "detail": "Periods were out of order, auto-sorted chronologically",
                    "source": "validate",
                }
                corrections.append(correction)
                audit_trail.append(correction)
                issues.append("Warning: Periods were out of order — auto-sorted")
        except Exception:
            pass

        # Coverage gaps
        try:
            dates = pd.to_datetime(df[temporal], format="%Y-%m", errors="coerce").dropna()
            if len(dates) >= 2:
                expected = pd.date_range(dates.min(), dates.max(), freq="MS")
                actual = set(dates.dt.to_period("M"))
                expected_set = set(expected.to_period("M"))
                gaps = expected_set - actual
                if gaps:
                    gap_strs = sorted([str(g) for g in gaps])
                    issues.append(f"Warning: Missing periods: {gap_strs}")
        except Exception:
            pass

    # ── Schema-specific validation rules ──

    for rule in schema.validation_rules:
        try:
            passed, message = rule.check(df)
            if message:
                issues.append(message)
            if not passed and rule.severity == "error":
                issues.append(f"ERROR: {rule.name} failed")
        except Exception as e:
            issues.append(f"Warning: Rule '{rule.name}' threw: {e}")

    # ── Derivation consistency (auto-correct) ──

    for deriv in schema.derivations:
        if deriv.target in df.columns:
            deps_present = all(d in df.columns for d in deriv.dependencies)
            if deps_present:
                try:
                    expected = df.apply(deriv.formula, axis=1)
                    actual = df[deriv.target]
                    diff = (actual - expected).abs()
                    max_diff = diff.max()
                    if max_diff > 1.0:
                        mean_val = actual.abs().mean()
                        pct = (max_diff / mean_val * 100) if mean_val > 0 else 0
                        if pct > 2.0:
                            msg = f"Warning: '{deriv.target}' off by ${max_diff:,.0f} ({pct:.1f}%). Auto-corrected."
                            issues.append(msg)
                            correction = {
                                "action": "auto_corrected",
                                "field": deriv.target,
                                "detail": f"Max diff ${max_diff:,.0f} ({pct:.1f}%), corrected via {deriv.description}",
                                "source": "validate",
                            }
                            corrections.append(correction)
                            audit_trail.append(correction)
                        df[deriv.target] = expected
                except Exception:
                    pass

    # ── Generic reasonableness checks ──

    _check_reasonableness(df, issues, schema.allows_duplicate_periods)

    has_errors = _has_errors(issues)
    return ValidationResult(
        is_valid=not has_errors,
        issues=issues,
        corrections=corrections,
    )


def _has_errors(issues: list[str]) -> bool:
    return any(i.startswith("ERROR:") for i in issues)


def _check_reasonableness(df: pd.DataFrame, issues: list[str], is_detail: bool = False):
    """Generic reasonableness checks that apply to any financial document."""

    # Revenue should be positive
    if "revenue" in df.columns:
        neg_count = (df["revenue"] < 0).sum()
        if neg_count > 0:
            issues.append(f"Warning: {neg_count} rows have negative revenue")

    # Gross margin between -50% and 100%
    if "revenue" in df.columns and "gross_profit" in df.columns:
        mask = df["revenue"] != 0
        if mask.any():
            margin = df.loc[mask, "gross_profit"] / df.loc[mask, "revenue"] * 100
            out_of_range = ((margin < -50) | (margin > 100)).sum()
            if out_of_range > 0:
                issues.append(f"Warning: {out_of_range} rows have gross margin outside [-50%, 100%]")

    # EBITDA margin between -100% and 100%
    if "revenue" in df.columns and "ebitda" in df.columns:
        mask = df["revenue"] != 0
        if mask.any():
            margin = df.loc[mask, "ebitda"] / df.loc[mask, "revenue"] * 100
            out_of_range = ((margin < -100) | (margin > 100)).sum()
            if out_of_range > 0:
                issues.append(f"Warning: {out_of_range} rows have EBITDA margin outside [-100%, 100%]")

    # MoM revenue change > 200% (skip for detail-level data with multiple rows per period)
    if "revenue" in df.columns and len(df) > 1 and not is_detail:
        pct_change = df["revenue"].pct_change().abs()
        spikes = pct_change[pct_change > 2.0]
        if len(spikes) > 0:
            spike_rows = spikes.index.tolist()
            issues.append(f"Warning: Revenue changed >200% MoM at rows {spike_rows}")

    # Operating expenses should be positive
    for col in ["sales_marketing", "rd", "ga", "total_opex", "cogs"]:
        if col in df.columns:
            neg = (df[col] < 0).sum()
            if neg > 0:
                issues.append(f"Warning: {neg} rows have negative {col}")
