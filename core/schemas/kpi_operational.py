"""
KPI / Operational Metrics schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class KpiOperationalSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "kpi_operational"

    @property
    def doc_type_name(self) -> str:
        return "KPI / Operational Metrics"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "kpi": 15, "operational metrics": 15, "unit economics": 12,
            "cac": 10, "ltv": 10, "churn": 10, "churn rate": 10,
            "nrr": 10, "net revenue retention": 12, "saas metrics": 12,
            "capacity utilization": 10, "throughput": 8, "yield": 6,
            "nps": 8, "net promoter": 8, "headcount": 4, "employee": 4,
            "retention": 6, "operational": 6, "metrics dashboard": 8,
            "kpi dashboard": 10,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "month", "period ending", "quarter"],
                           description="Time period (month/quarter/year)"),
            FieldDefinition("metric_name", "Metric Name", required=False, is_financial=False,
                           aliases=["kpi", "metric", "indicator", "measure"],
                           description="KPI or metric name (for long-format data where KPIs are rows)"),
            FieldDefinition("metric_value", "Metric Value", required=False,
                           aliases=["value", "amount", "result"],
                           description="KPI or metric value (for long-format data)"),
            FieldDefinition("total_headcount", "Total Headcount", required=False,
                           aliases=["headcount", "employees", "fte", "ftes", "total employees"],
                           description="Total employee headcount or FTEs"),
            FieldDefinition("revenue_per_employee", "Revenue per Employee", required=False,
                           aliases=["rev per employee", "revenue/employee", "rev/fte"],
                           description="Revenue divided by headcount"),
            FieldDefinition("ebitda_per_employee", "EBITDA per Employee", required=False,
                           aliases=["ebitda/employee", "ebitda per fte"],
                           description="EBITDA divided by headcount"),
            FieldDefinition("cac", "CAC", required=False,
                           aliases=["customer acquisition cost", "acquisition cost"],
                           description="Customer acquisition cost"),
            FieldDefinition("ltv", "LTV", required=False,
                           aliases=["lifetime value", "customer lifetime value", "clv"],
                           description="Customer lifetime value"),
            FieldDefinition("ltv_cac_ratio", "LTV:CAC Ratio", required=False,
                           aliases=["ltv:cac", "ltv/cac", "ltv to cac"],
                           description="Ratio of lifetime value to customer acquisition cost"),
            FieldDefinition("payback_months", "Payback Months", required=False,
                           aliases=["cac payback", "payback period", "payback"],
                           description="CAC payback period in months"),
            FieldDefinition("monthly_churn_rate", "Monthly Churn Rate", required=False,
                           aliases=["churn", "churn rate", "monthly churn", "logo churn"],
                           description="Monthly customer or logo churn rate"),
            FieldDefinition("net_revenue_retention", "Net Revenue Retention", required=False,
                           aliases=["nrr", "net retention", "net dollar retention", "ndr"],
                           description="Net revenue retention rate"),
            FieldDefinition("gross_revenue_retention", "Gross Revenue Retention", required=False,
                           aliases=["grr", "gross retention"],
                           description="Gross revenue retention rate"),
            FieldDefinition("capacity_utilization", "Capacity Utilization", required=False,
                           aliases=["utilization", "capacity", "utilization rate", "util %"],
                           description="Capacity utilization rate"),
            FieldDefinition("yield_rate", "Yield Rate", required=False,
                           aliases=["yield", "production yield", "quality yield"],
                           description="Production or quality yield rate"),
            FieldDefinition("throughput", "Throughput", required=False,
                           aliases=["output", "production rate", "units per hour"],
                           description="Production throughput or output rate"),
            FieldDefinition("nps_score", "NPS Score", required=False,
                           aliases=["nps", "net promoter score", "net promoter"],
                           description="Net Promoter Score"),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="ltv_cac_ratio",
                dependencies=["ltv", "cac"],
                formula=lambda row: row["ltv"] / row["cac"] if row.get("cac") and row["cac"] != 0 else None,
                description="ltv / cac",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Monthly churn rate between 0 and 100",
                check=lambda df: _check_range(df, "monthly_churn_rate", 0, 100,
                                              "Monthly churn rate"),
                severity="warning",
            ),
            ValidationRule(
                name="Net revenue retention between 50 and 200",
                check=lambda df: _check_range(df, "net_revenue_retention", 50, 200,
                                              "Net revenue retention"),
                severity="warning",
            ),
            ValidationRule(
                name="NPS score between -100 and 100",
                check=lambda df: _check_range(df, "nps_score", -100, 100, "NPS score"),
                severity="warning",
            ),
            ValidationRule(
                name="LTV:CAC ratio > 0",
                check=lambda df: _check_positive(df, "ltv_cac_ratio", "LTV:CAC ratio"),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_range(df: pd.DataFrame, field: str, low: float, high: float, label: str) -> tuple[bool, str]:
    """Check if a field's values fall within an expected range."""
    if field not in df.columns:
        return True, ""
    try:
        values = df[field].dropna()
        if values.empty:
            return True, ""
        out_of_range = (values < low) | (values > high)
        if out_of_range.any():
            min_val = values.min()
            max_val = values.max()
            return True, f"Warning: {label} has values {min_val:.2f}-{max_val:.2f}, expected {low}-{high}"
        return True, ""
    except Exception:
        return True, ""


def _check_positive(df: pd.DataFrame, field: str, label: str) -> tuple[bool, str]:
    """Check if a field's values are positive."""
    if field not in df.columns:
        return True, ""
    try:
        values = df[field].dropna()
        if values.empty:
            return True, ""
        if (values <= 0).any():
            return True, f"Warning: {label} has non-positive values"
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(KpiOperationalSchema())
