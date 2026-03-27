"""
Cost / Expense Detail schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class CostDetailSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "cost_detail"

    @property
    def doc_type_name(self) -> str:
        return "Cost / Expense Detail"

    @property
    def allows_duplicate_periods(self) -> bool:
        return True

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "cost detail": 15, "expense detail": 15, "cost breakdown": 12,
            "expense breakdown": 12, "vendor spend": 12, "procurement": 10,
            "headcount": 8, "payroll": 10, "compensation": 8,
            "department expense": 10, "cost center": 8, "spend analysis": 10,
            "cost by": 8, "expense by": 8, "spend by": 8, "opex detail": 8,
            # Column-level signals that distinguish from P&L
            "cost_category": 12, "cost_subcategory": 12, "subcategory": 10,
            "vendor": 10, "supplier": 10, "department": 8, "dept": 6,
            "contractor": 8, "benefits": 6, "facilities": 6,
            "amount": 4,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "month", "period ending"],
                           description="Time period (month/quarter/year)"),
            FieldDefinition("amount", "Amount", required=True,
                           aliases=["cost", "expense", "total cost", "total expense", "spend", "total amount", "total spend"],
                           description="Cost or expense amount"),
            FieldDefinition("cost_category", "Cost Category", required=False, is_financial=False,
                           aliases=["category", "expense category", "type", "expense type", "cost type"],
                           description="High-level cost category"),
            FieldDefinition("cost_subcategory", "Cost Subcategory", required=False, is_financial=False,
                           aliases=["subcategory", "sub-category", "detail", "line item"],
                           description="Detailed cost subcategory or line item"),
            FieldDefinition("department", "Department", required=False, is_financial=False,
                           aliases=["dept", "cost center", "division", "team", "business unit"],
                           description="Department or cost center"),
            FieldDefinition("vendor", "Vendor", required=False, is_financial=False,
                           aliases=["supplier", "vendor name", "payee", "company"],
                           description="Vendor or supplier name"),
            FieldDefinition("headcount", "Headcount", required=False,
                           aliases=["fte", "ftes", "employees", "hc", "head count", "employee count"],
                           description="Number of employees or FTEs"),
            FieldDefinition("compensation", "Compensation", required=False,
                           aliases=["salaries", "wages", "salary", "total comp", "payroll", "base salary"],
                           description="Total compensation expense"),
            FieldDefinition("benefits", "Benefits", required=False,
                           aliases=["benefit cost", "employee benefits", "health insurance"],
                           description="Employee benefits expense"),
            FieldDefinition("contractor_spend", "Contractor Spend", required=False,
                           aliases=["contractors", "consulting", "professional services", "outsourced"],
                           description="Contractor or consulting spend"),
            FieldDefinition("materials_cost", "Materials Cost", required=False,
                           aliases=["raw materials", "materials", "direct materials"],
                           description="Raw materials or direct materials cost"),
            FieldDefinition("freight_cost", "Freight Cost", required=False,
                           aliases=["shipping", "freight", "logistics", "transportation"],
                           description="Shipping, freight, or logistics cost"),
            FieldDefinition("facilities_cost", "Facilities Cost", required=False,
                           aliases=["rent", "facilities", "occupancy", "office", "utilities"],
                           description="Facilities, rent, or occupancy cost"),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return []

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Amount should be positive",
                check=lambda df: (True, "") if "amount" not in df.columns or (df["amount"] >= 0).all()
                    else (True, "Warning: Some rows have negative cost/expense amounts"),
                severity="warning",
            ),
            ValidationRule(
                name="Avg compensation per head $20K-$500K annually",
                check=lambda df: _check_avg_comp_per_head(df),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_avg_comp_per_head(df: pd.DataFrame) -> tuple[bool, str]:
    """Check if average compensation per headcount is within reasonable range."""
    if "headcount" not in df.columns or "compensation" not in df.columns:
        return True, ""
    try:
        mask = df["headcount"].notna() & df["compensation"].notna() & (df["headcount"] > 0)
        subset = df[mask]
        if subset.empty:
            return True, ""
        avg_comp = subset["compensation"] / subset["headcount"]
        # Annualize if monthly (multiply by 12) — use raw value as a conservative check
        # Check against annual range; if monthly data, values ~$1.7K-$42K per month
        min_annual = 20_000
        max_annual = 500_000
        # Check if any row falls outside annual range (assume data could be monthly or annual)
        out_of_range = (avg_comp < min_annual / 12) | (avg_comp > max_annual)
        if out_of_range.any():
            min_val = avg_comp.min()
            max_val = avg_comp.max()
            return True, f"Warning: Avg comp per head ranges ${min_val:,.0f}-${max_val:,.0f} — verify periodicity"
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(CostDetailSchema())
