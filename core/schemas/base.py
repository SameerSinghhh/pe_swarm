"""
Abstract base class for all document type schemas.

Every financial document type (P&L, Balance Sheet, etc.) is a subclass
of DocumentSchema. Each defines its fields, derivation rules, validation
rules, classification keywords, and normalization prompt.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


@dataclass
class FieldDefinition:
    """One field in a schema."""
    name: str
    display_name: str
    required: bool = True
    is_financial: bool = True
    is_temporal: bool = False
    aliases: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DerivationRule:
    """A field that can be computed from other fields."""
    target: str
    dependencies: list[str]
    formula: Callable[[pd.Series], float]
    description: str = ""


@dataclass
class ValidationRule:
    """A consistency check on the normalized data."""
    name: str
    check: Callable[[pd.DataFrame], tuple[bool, str]]
    severity: str = "error"  # "error" or "warning"


class DocumentSchema(ABC):
    """Abstract base for all document type schemas."""

    @property
    @abstractmethod
    def doc_type_id(self) -> str:
        """Unique identifier, e.g. 'income_statement'."""

    @property
    @abstractmethod
    def doc_type_name(self) -> str:
        """Human-readable name, e.g. 'Income Statement / P&L'."""

    @property
    @abstractmethod
    def classification_keywords(self) -> dict[str, int]:
        """Keywords → scores for document classification."""

    @property
    @abstractmethod
    def fields(self) -> list[FieldDefinition]:
        """All fields in this schema."""

    @property
    @abstractmethod
    def derivations(self) -> list[DerivationRule]:
        """Fields that can be computed from others."""

    @property
    @abstractmethod
    def validation_rules(self) -> list[ValidationRule]:
        """Consistency checks for this document type."""

    @abstractmethod
    def build_normalization_prompt(
        self,
        preview: str,
        columns: list[str],
        sample_values: dict,
        context: dict,
    ) -> str:
        """Build the Claude prompt for normalizing this document type."""

    @property
    def allows_duplicate_periods(self) -> bool:
        """Override to True for detail-level schemas (revenue by product, cost by dept)."""
        return False

    @property
    def temporal_field(self) -> str:
        for f in self.fields:
            if f.is_temporal:
                return f.name
        return "period"

    @property
    def required_fields(self) -> list[str]:
        return [f.name for f in self.fields if f.required]

    @property
    def optional_fields(self) -> list[str]:
        return [f.name for f in self.fields if not f.required]

    @property
    def financial_fields(self) -> list[str]:
        return [f.name for f in self.fields if f.is_financial]

    @property
    def all_field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def get_field(self, name: str) -> FieldDefinition | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def _build_schema_description(self) -> str:
        """Build a text description of the target schema for the AI prompt."""
        lines = []
        for f in self.fields:
            req = "REQUIRED" if f.required else "optional"
            aliases = f", aliases: {', '.join(f.aliases)}" if f.aliases else ""
            lines.append(f"- {f.name}: {f.description} [{req}]{aliases}")
        return "\n".join(lines)

    def _build_derivations_description(self) -> str:
        """Build a text description of derivation rules for the AI prompt."""
        if not self.derivations:
            return "None"
        lines = []
        for d in self.derivations:
            lines.append(f"- {d.target} = {d.description}")
        return "\n".join(lines)

    def _build_mapping_json_template(self) -> str:
        """Build the JSON template showing all fields for the AI response."""
        lines = []
        for f in self.fields:
            lines.append(f'    "{f.name}": "<source column>" or ["<col1>", "<col2>"] or null')
        return "{\n" + ",\n".join(lines) + "\n  }"

    def build_normalization_prompt(
        self,
        preview: str,
        columns: list[str],
        sample_values: dict,
        context: dict,
    ) -> str:
        """Default normalization prompt. Subclasses can override for special cases."""
        business_type = context.get("business_type", "Not specified")
        pre_header = context.get("pre_header_context", "")
        row_count = context.get("row_count", 0)
        header_row_idx = context.get("header_row_idx", 0)
        profile_text = context.get("profile_text", "")
        sample_str = "\n".join(f"  {col}: {vals}" for col, vals in sample_values.items())

        schema_desc = self._build_schema_description()
        derivation_desc = self._build_derivations_description()
        mapping_template = self._build_mapping_json_template()

        profile_section = f"\n{profile_text}\n" if profile_text else ""

        return f"""You are a financial data normalization engine for a private equity analytics platform.

This is a {self.doc_type_name} document.

TARGET SCHEMA:
{schema_desc}

DERIVABLE FIELDS (compute if not present in source):
{derivation_desc}

BUSINESS TYPE: {business_type}
{profile_section}
{pre_header}SOURCE DATA:
Column names: {columns}
Total data rows: {row_count}
Header was detected at row index: {header_row_idx}

{preview}

Sample values per column:
{sample_str}

INSTRUCTIONS:
1. Map each target field to one or more source columns. If summing multiple columns, provide a list.
2. If a field can be derived from other fields, include it in "derivations_needed".
3. If a field cannot be mapped or derived, set to null.
4. Identify rows to skip (totals, subtotals, blanks, notes). Use 0-based indices.
5. If values are in thousands ($000s) or millions ($M), set multiplier accordingly.

Return ONLY this JSON:
{{
  "column_mapping": {mapping_template},
  "derivations_needed": ["<fields to compute>"],
  "skip_rows": [<0-based row indices to exclude>],
  "month_format": "<e.g. YYYY-MM, MMM-YY, January 2025>",
  "multiplier": 1 or 1000 or 1000000,
  "notes": "<brief explanation>"
}}

No markdown. No code fences. Only the JSON object."""
