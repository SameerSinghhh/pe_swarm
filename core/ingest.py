"""
Universal financial data ingestion pipeline.

Entry point: ingest_file()

Pipeline:
1. Read file → 2. Classify → 3. Profile raw → 4. Normalize → 5. Validate → 6. Profile output → 7. Return
"""

import os
from pathlib import Path

from core.readers import read_file, FileReadError
from core.classify import classify_document
from core.normalize import (
    check_already_normalized, clean_normalized,
    ai_normalize, apply_mapping, MappingError,
)
from core.validate import validate
from core.result import NormalizedResult


class IngestError(Exception):
    """Base exception for ingestion failures."""


class ValidationError(IngestError):
    """Normalized data fails consistency checks."""


def ingest_file(
    filepath: str,
    company_name: str = "",
    business_type: str = "",
    doc_type_hint: str | None = None,
) -> NormalizedResult:
    """
    Universal entry point. Takes any financial file and returns a NormalizedResult.
    """
    filepath = str(Path(filepath).resolve())
    if not os.path.exists(filepath):
        raise FileReadError(f"File not found: {filepath}")

    audit_trail: list[dict] = []

    # Phase 1: Read raw data
    raw_df, metadata = read_file(filepath)

    # Phase 2: Classify document type
    schema, classification_confidence = classify_document(raw_df, metadata, doc_type_hint)

    # Phase 2.5: Profile raw data (if profiler available)
    raw_profile = None
    profile_text = ""
    try:
        from core.profiler import profile_raw, format_profile_for_prompt
        raw_profile = profile_raw(raw_df, schema)
        profile_text = format_profile_for_prompt(raw_profile)
    except ImportError:
        pass  # profiler not yet built

    # Phase 3: Fast path — already normalized?
    if check_already_normalized(raw_df, schema):
        df = clean_normalized(raw_df, schema, audit_trail)
        vr = validate(df, schema, audit_trail)
        if not vr.is_valid:
            errors = [i for i in vr.issues if i.startswith("ERROR:")]
            raise ValidationError(f"Validation failed: {'; '.join(errors)}")

        # Profile output
        quality_score, quality_report = _profile_output(df, schema, audit_trail)

        return NormalizedResult(
            df=df,
            doc_type=schema.doc_type_id,
            doc_type_name=schema.doc_type_name,
            company_name=company_name,
            business_type=business_type,
            source_file=filepath,
            used_ai=False,
            classification_confidence=classification_confidence,
            warnings=[i for i in vr.issues if not i.startswith("ERROR:")],
            audit_trail=audit_trail,
            quality_score=quality_score,
            raw_profile=raw_profile,
            quality_report=quality_report,
            metadata=metadata,
        )

    # Phase 4-5: AI normalization with fallback
    try:
        mapping = ai_normalize(raw_df, metadata, schema, business_type, profile_text)
        df, unmapped = apply_mapping(raw_df, mapping, schema, audit_trail)
        vr = validate(df, schema, audit_trail)

        if not vr.is_valid:
            raise ValidationError(f"Validation failed after AI normalization")

    except (MappingError, ValidationError) as primary_error:
        # Try code-gen fallback
        try:
            from core.fallback import attempt_code_fallback
            fallback_result = attempt_code_fallback(
                raw_df, metadata, schema, str(primary_error),
                business_type, raw_profile,
            )
            df = fallback_result.df
            unmapped = []
            audit_trail.append({
                "action": "fallback_used",
                "field": "",
                "detail": f"Code-gen fallback triggered due to: {primary_error}",
                "source": "ingest",
            })
            vr = validate(df, schema, audit_trail)
            if not vr.is_valid:
                errors = [i for i in vr.issues if i.startswith("ERROR:")]
                raise IngestError(
                    f"Fallback also failed validation: {'; '.join(errors)}"
                )

            quality_score, quality_report = _profile_output(df, schema, audit_trail)

            return NormalizedResult(
                df=df,
                doc_type=schema.doc_type_id,
                doc_type_name=schema.doc_type_name,
                company_name=company_name,
                business_type=business_type,
                source_file=filepath,
                used_ai=True,
                used_fallback=True,
                fallback_code=fallback_result.code,
                classification_confidence=classification_confidence,
                warnings=[i for i in vr.issues if not i.startswith("ERROR:")],
                unmapped_fields=unmapped,
                audit_trail=audit_trail,
                quality_score=quality_score,
                raw_profile=raw_profile,
                quality_report=quality_report,
                metadata={**metadata, "fallback_explanation": fallback_result.explanation},
            )
        except ImportError:
            # fallback module not yet built — re-raise original error
            raise primary_error
        except Exception as fallback_error:
            raise IngestError(
                f"Primary error: {primary_error}. Fallback also failed: {fallback_error}"
            )

    # Phase 6: Profile output
    quality_score, quality_report = _profile_output(df, schema, audit_trail)

    return NormalizedResult(
        df=df,
        doc_type=schema.doc_type_id,
        doc_type_name=schema.doc_type_name,
        company_name=company_name,
        business_type=business_type,
        source_file=filepath,
        used_ai=True,
        classification_confidence=classification_confidence,
        warnings=[i for i in vr.issues if not i.startswith("ERROR:")],
        unmapped_fields=unmapped,
        audit_trail=audit_trail,
        quality_score=quality_score,
        raw_profile=raw_profile,
        quality_report=quality_report,
        metadata={**metadata, "mapping_notes": mapping.get("notes", "")},
    )


def _profile_output(df, schema, audit_trail) -> tuple[float, object]:
    """Profile the normalized output. Returns (quality_score, quality_report)."""
    try:
        from core.profiler import profile_normalized
        quality_report = profile_normalized(df, schema, audit_trail)
        return quality_report.quality_score, quality_report
    except ImportError:
        return 0.0, None
