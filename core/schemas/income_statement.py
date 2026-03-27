"""
Income Statement / P&L schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class IncomeStatementSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "income_statement"

    @property
    def doc_type_name(self) -> str:
        return "Income Statement / P&L"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "p&l": 15, "income statement": 15, "profit and loss": 15, "profit & loss": 15,
            "ebitda": 12, "operating income": 10, "net income": 8,
            "revenue": 5, "cogs": 8, "cost of goods": 8, "cost of revenue": 8,
            "gross profit": 10, "gross margin": 8,
            "opex": 8, "operating expense": 8,
            "sales & marketing": 6, "sales_marketing": 6,
            "research": 4, "development": 4, "r&d": 6,
            "general & admin": 6, "g&a": 6,
            "sg&a": 6, "sga": 6,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["month", "date", "mo.", "period ending", "month ending"],
                           description="Time period (month/quarter/year)"),
            FieldDefinition("revenue", "Revenue", required=True,
                           aliases=["total revenue", "net revenue", "sales", "total income", "net sales", "total sales", "rev"],
                           description="Top-line revenue"),
            FieldDefinition("cogs", "Cost of Goods Sold", required=True,
                           aliases=["cost of goods sold", "cost of revenue", "cost of sales", "cos", "cost of service delivery", "total cogs", "direct costs"],
                           description="Cost of goods sold. For manufacturing: sum materials + labor + overhead. For services: cost of service delivery."),
            FieldDefinition("gross_profit", "Gross Profit", required=True,
                           aliases=["gross margin", "gp"],
                           description="Revenue minus COGS. Can be derived."),
            FieldDefinition("sales_marketing", "Sales & Marketing", required=True,
                           aliases=["s&m", "sales and marketing", "sales & marketing expense", "selling expenses", "selling expense", "sg&a", "sga"],
                           description="Sales & marketing expense. If only SG&A exists, map SG&A here."),
            FieldDefinition("rd", "R&D", required=False,
                           aliases=["research and development", "r&d", "r&d costs", "engineering", "eng", "technology", "technology & development", "product development"],
                           description="Research & development expense"),
            FieldDefinition("ga", "G&A", required=False,
                           aliases=["general and administrative", "general & administrative", "admin expenses", "admin", "g&a"],
                           description="General & administrative expense. Null if lumped into SG&A."),
            FieldDefinition("total_opex", "Total OpEx", required=True,
                           aliases=["total operating expenses", "total expenses", "total operating exp", "ttl opex", "operating expenses"],
                           description="Total operating expenses below gross profit. Can be derived."),
            FieldDefinition("ebitda", "EBITDA", required=True,
                           aliases=["operating income", "net operating income", "ebit"],
                           description="Earnings before interest, taxes, depreciation, amortization. Can be derived."),
            FieldDefinition("budget_revenue", "Budget Revenue", required=False,
                           aliases=["bgt rev", "budgeted revenue", "target revenue", "plan revenue"],
                           description="Budgeted revenue"),
            FieldDefinition("budget_ebitda", "Budget EBITDA", required=False,
                           aliases=["bgt ebitda", "budgeted ebitda", "target ebitda", "plan ebitda"],
                           description="Budgeted EBITDA"),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="gross_profit",
                dependencies=["revenue", "cogs"],
                formula=lambda row: row["revenue"] - row["cogs"],
                description="revenue - cogs",
            ),
            DerivationRule(
                target="total_opex",
                dependencies=["sales_marketing"],
                formula=lambda row: row.get("sales_marketing", 0) + row.get("rd", 0) + row.get("ga", 0),
                description="sales_marketing + rd + ga",
            ),
            DerivationRule(
                target="ebitda",
                dependencies=["gross_profit", "total_opex"],
                formula=lambda row: row["gross_profit"] - row["total_opex"],
                description="gross_profit - total_opex",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Gross profit = Revenue - COGS",
                check=lambda df: _check_derivation(df, "gross_profit", lambda r: r["revenue"] - r["cogs"]),
                severity="warning",
            ),
            ValidationRule(
                name="EBITDA = Gross Profit - Total OpEx",
                check=lambda df: _check_derivation(df, "ebitda", lambda r: r["gross_profit"] - r["total_opex"]),
                severity="warning",
            ),
            ValidationRule(
                name="Revenue should be positive",
                check=lambda df: (True, "") if (df["revenue"] >= 0).all() else (True, "Warning: Some months have negative revenue"),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_derivation(df: pd.DataFrame, field: str, formula) -> tuple[bool, str]:
    """Check if a derived field matches its formula."""
    if field not in df.columns:
        return True, ""
    try:
        expected = df.apply(formula, axis=1)
        actual = df[field]
        diff = (actual - expected).abs()
        max_diff = diff.max()
        if max_diff > 1.0:
            pct = (max_diff / actual.abs().mean()) * 100 if actual.abs().mean() > 0 else 0
            if pct > 2.0:
                return True, f"Warning: '{field}' off by up to ${max_diff:,.0f} ({pct:.1f}%). Auto-corrected."
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(IncomeStatementSchema())
