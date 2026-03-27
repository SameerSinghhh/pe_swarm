"""
NormalizedResult — the universal output of the ingestion pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from core.profiler import DataProfile, QualityReport


@dataclass
class NormalizedResult:
    """A validated, schema-conforming DataFrame ready for downstream analysis."""
    df: pd.DataFrame

    # Classification
    doc_type: str = ""
    doc_type_name: str = ""
    classification_confidence: str = ""

    # Context
    company_name: str = ""
    business_type: str = ""
    source_file: str = ""

    # Normalization
    used_ai: bool = False
    used_fallback: bool = False
    fallback_code: str = ""

    # Issues
    warnings: list[str] = field(default_factory=list)
    unmapped_fields: list[str] = field(default_factory=list)

    # Quality
    quality_score: float = 0.0
    audit_trail: list[dict] = field(default_factory=list)
    raw_profile: "DataProfile | None" = None
    quality_report: "QualityReport | None" = None

    # Extra
    metadata: dict = field(default_factory=dict)
