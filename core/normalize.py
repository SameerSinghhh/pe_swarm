"""
AI normalization engine. Sends file previews to Claude and applies the returned mapping.
Tracks all transformations in an audit trail.
"""

import json
import os

import pandas as pd
from dotenv import load_dotenv

from core.schemas.base import DocumentSchema
from core.cleaning import (
    to_numeric, parse_period, detect_header_row,
    build_preview, get_pre_header_context,
)

load_dotenv()


class MappingError(Exception):
    """Claude could not produce a valid column mapping."""


def check_already_normalized(df: pd.DataFrame, schema: DocumentSchema) -> bool:
    """Check if the DataFrame already matches the schema (fast path).
    Checks both canonical field names and aliases."""
    if df.empty:
        return False
    cols = {str(c).strip().lower() for c in df.columns if isinstance(c, str)}

    for field_def in schema.fields:
        if not field_def.required:
            continue
        found = field_def.name.lower() in cols
        if not found:
            found = any(alias.lower() in cols for alias in field_def.aliases)
        if not found:
            return False
    return True


def clean_normalized(
    df: pd.DataFrame,
    schema: DocumentSchema,
    audit_trail: list[dict] | None = None,
) -> pd.DataFrame:
    """Clean a DataFrame that already has the right columns. Renames aliases to canonical names."""
    if audit_trail is None:
        audit_trail = []

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Rename alias columns to canonical names
    rename_map = {}
    for field_def in schema.fields:
        canonical = field_def.name.lower()
        if canonical in df.columns:
            continue
        for alias in field_def.aliases:
            if alias.lower() in df.columns:
                rename_map[alias.lower()] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
        for old, new in rename_map.items():
            audit_trail.append({
                "action": "renamed",
                "field": new,
                "detail": f"Column '{old}' renamed to '{new}'",
                "source": "clean_normalized",
            })

    for col in schema.financial_fields:
        if col in df.columns:
            df[col] = to_numeric(df[col])

    temporal = schema.temporal_field
    if temporal in df.columns:
        df[temporal] = df[temporal].apply(parse_period)

    # Drop all-NaN financial rows
    financial_present = [c for c in schema.financial_fields if c in df.columns]
    if financial_present:
        before = len(df)
        df = df.dropna(subset=financial_present, how="all")
        dropped = before - len(df)
        if dropped > 0:
            audit_trail.append({
                "action": "row_dropped",
                "field": "",
                "detail": f"Dropped {dropped} all-NaN rows",
                "source": "clean_normalized",
            })

    return df.reset_index(drop=True)


def ai_normalize(
    raw_df: pd.DataFrame,
    metadata: dict,
    schema: DocumentSchema,
    business_type: str = "",
    profile_text: str = "",
) -> dict:
    """Use Claude to understand the file and produce a column mapping."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise MappingError("anthropic package required. Install: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise MappingError(
            "ANTHROPIC_API_KEY not set. AI normalization required for non-standard files."
        )

    header_row_idx, df_with_header = detect_header_row(raw_df)
    pre_header = get_pre_header_context(raw_df, header_row_idx)
    preview = build_preview(df_with_header)
    columns = [str(c) for c in df_with_header.columns]

    sample_values = {}
    for col in df_with_header.columns:
        vals = df_with_header[col].dropna().unique()
        sample_values[str(col)] = [str(v) for v in vals[:3]]

    context = {
        "business_type": business_type or "Not specified",
        "pre_header_context": pre_header,
        "row_count": len(df_with_header),
        "header_row_idx": header_row_idx,
        "profile_text": profile_text,
    }

    prompt = schema.build_normalization_prompt(preview, columns, sample_values, context)

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        mapping = json.loads(text)
    except json.JSONDecodeError:
        retry = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": text},
                {"role": "user", "content": "That was not valid JSON. Return ONLY a valid JSON object."},
            ],
        )
        retry_text = retry.content[0].text.strip()
        if retry_text.startswith("```"):
            retry_text = "\n".join(retry_text.split("\n")[1:])
            if retry_text.endswith("```"):
                retry_text = retry_text[:-3].strip()
        try:
            mapping = json.loads(retry_text)
        except json.JSONDecodeError:
            raise MappingError(f"Claude returned invalid JSON after retry:\n{retry_text}")

    mapping["_header_row_idx"] = header_row_idx
    mapping["_raw_df"] = raw_df
    return mapping


def apply_mapping(
    raw_df: pd.DataFrame,
    mapping: dict,
    schema: DocumentSchema,
    audit_trail: list[dict] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Transform the raw DataFrame using Claude's mapping.
    Returns (normalized_df, list_of_unmapped_fields).
    Appends transformations to audit_trail.
    """
    if audit_trail is None:
        audit_trail = []

    source_df = mapping.get("_raw_df", raw_df)
    _, df = detect_header_row(source_df)

    col_mapping = mapping.get("column_mapping", {})
    skip_rows = mapping.get("skip_rows", [])
    multiplier = mapping.get("multiplier", 1)
    derivations_needed = mapping.get("derivations_needed", [])

    # Drop skip rows
    if skip_rows:
        valid_skip = [i for i in skip_rows if 0 <= i < len(df)]
        if valid_skip:
            df = df.drop(df.index[valid_skip]).reset_index(drop=True)
            audit_trail.append({
                "action": "row_dropped",
                "field": "",
                "detail": f"Skipped {len(valid_skip)} rows (totals/subtotals/notes)",
                "source": "apply_mapping",
            })

    # Drop empty rows
    before = len(df)
    df = df.dropna(how="all").reset_index(drop=True)
    blank_dropped = before - len(df)
    if blank_dropped:
        audit_trail.append({
            "action": "row_dropped",
            "field": "",
            "detail": f"Dropped {blank_dropped} blank rows",
            "source": "apply_mapping",
        })

    # Build normalized DataFrame
    result = pd.DataFrame()
    unmapped = []
    temporal_field = schema.temporal_field

    for field_def in schema.fields:
        fname = field_def.name
        source = col_mapping.get(fname)

        if source is None:
            if not field_def.required:
                continue
            if fname in derivations_needed:
                continue
            unmapped.append(fname)
            continue

        if isinstance(source, list):
            actual_cols = _find_columns_ci(source, df.columns)
            if not actual_cols:
                unmapped.append(fname)
                continue
            numeric_cols = df[actual_cols].apply(to_numeric)
            result[fname] = numeric_cols.sum(axis=1)
            audit_trail.append({
                "action": "mapped_sum",
                "field": fname,
                "detail": f"Summed columns: {actual_cols}",
                "source": "apply_mapping",
            })
        else:
            matched_col = _find_column_ci(source, df.columns)
            if matched_col is None:
                if field_def.required and fname not in derivations_needed:
                    unmapped.append(fname)
                continue

            if field_def.is_temporal:
                result[fname] = df[matched_col].astype(str).str.strip()
            else:
                result[fname] = to_numeric(df[matched_col])

    # Apply multiplier
    if multiplier != 1:
        for col in result.columns:
            if col != temporal_field and pd.api.types.is_numeric_dtype(result[col]):
                result[col] = result[col] * multiplier
        audit_trail.append({
            "action": "multiplier_applied",
            "field": "",
            "detail": f"All financial values multiplied by {multiplier}",
            "source": "apply_mapping",
        })

    # Fill missing required fields with 0
    for field_def in schema.fields:
        fname = field_def.name
        if (fname not in result.columns
            and not field_def.is_temporal
            and fname not in derivations_needed
            and col_mapping.get(fname) is None
            and field_def.required):
            result[fname] = 0.0
            audit_trail.append({
                "action": "auto_fill_zero",
                "field": fname,
                "detail": f"Required field '{fname}' not in source, filled with 0",
                "source": "apply_mapping",
            })

    # Derive missing fields
    for deriv in schema.derivations:
        if deriv.target in derivations_needed or deriv.target not in result.columns:
            deps_present = all(d in result.columns for d in deriv.dependencies)
            if deps_present:
                try:
                    result[deriv.target] = result.apply(deriv.formula, axis=1)
                    audit_trail.append({
                        "action": "derived",
                        "field": deriv.target,
                        "detail": f"Computed: {deriv.description}",
                        "source": "apply_mapping",
                    })
                except Exception:
                    if deriv.target not in result.columns:
                        unmapped.append(deriv.target)

    # Parse temporal field
    if temporal_field in result.columns:
        before = len(result)
        result[temporal_field] = result[temporal_field].apply(parse_period)
        result = result[result[temporal_field].notna()].reset_index(drop=True)
        dropped = before - len(result)
        if dropped:
            audit_trail.append({
                "action": "row_dropped",
                "field": temporal_field,
                "detail": f"Dropped {dropped} rows with unparseable periods",
                "source": "apply_mapping",
            })

    return result, unmapped


def _find_column_ci(name: str, columns) -> str | None:
    """Find a column by name, case-insensitive."""
    if name in columns:
        return name
    for col in columns:
        if str(col).strip().lower() == str(name).strip().lower():
            return col
    return None


def _find_columns_ci(names: list[str], columns) -> list[str]:
    """Find multiple columns by name, case-insensitive."""
    result = []
    for name in names:
        matched = _find_column_ci(name, columns)
        if matched:
            result.append(matched)
    return result
