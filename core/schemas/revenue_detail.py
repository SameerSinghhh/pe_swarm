"""
Revenue Detail schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class RevenueDetailSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "revenue_detail"

    @property
    def doc_type_name(self) -> str:
        return "Revenue Detail"

    @property
    def allows_duplicate_periods(self) -> bool:
        return True

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "revenue detail": 15, "revenue by customer": 15, "revenue by product": 15,
            "revenue breakdown": 12, "sales detail": 12, "customer revenue": 10,
            "product revenue": 10, "revenue by segment": 10, "revenue by geography": 8,
            "mrr": 6, "arr": 6, "bookings": 6, "pipeline": 4,
            "sales by": 8, "revenue analysis": 8,
            # Column-level signals that distinguish from P&L
            "customer": 8, "product": 8, "segment": 6, "geography": 6, "channel": 6,
            "units_sold": 10, "unit_price": 10, "units": 4, "qty": 6, "quantity": 6,
            "customer_count": 8, "sku": 8, "territory": 6,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "month", "period ending", "month ending"],
                           description="Time period (month/quarter/year)"),
            FieldDefinition("revenue", "Revenue", required=True,
                           aliases=["amount", "total revenue", "net revenue", "sales", "total sales", "total amount"],
                           description="Revenue amount"),
            FieldDefinition("customer", "Customer", required=False, is_financial=False,
                           aliases=["customer name", "client", "client name", "account name", "account"],
                           description="Customer or account name"),
            FieldDefinition("product", "Product", required=False, is_financial=False,
                           aliases=["product name", "sku", "item", "service", "product/service"],
                           description="Product, SKU, or service name"),
            FieldDefinition("segment", "Segment", required=False, is_financial=False,
                           aliases=["business segment", "business unit", "division", "segment name"],
                           description="Business segment or division"),
            FieldDefinition("geography", "Geography", required=False, is_financial=False,
                           aliases=["region", "country", "territory", "market", "geo"],
                           description="Geographic region or market"),
            FieldDefinition("channel", "Channel", required=False, is_financial=False,
                           aliases=["sales channel", "distribution channel", "source"],
                           description="Sales or distribution channel"),
            FieldDefinition("units_sold", "Units Sold", required=False,
                           aliases=["quantity", "units", "volume", "qty"],
                           description="Number of units sold"),
            FieldDefinition("unit_price", "Unit Price", required=False,
                           aliases=["price", "avg price", "average price", "price per unit", "asp"],
                           description="Price per unit or average selling price"),
            FieldDefinition("new_revenue", "New Revenue", required=False,
                           aliases=["new business", "new customer revenue", "new logos"],
                           description="Revenue from new customers"),
            FieldDefinition("expansion_revenue", "Expansion Revenue", required=False,
                           aliases=["upsell", "cross-sell", "expansion", "upsell revenue"],
                           description="Revenue from upsell or cross-sell"),
            FieldDefinition("churned_revenue", "Churned Revenue", required=False,
                           aliases=["churn", "lost revenue", "churned", "contraction"],
                           description="Revenue lost from churn or contraction"),
            FieldDefinition("mrr", "MRR", required=False,
                           aliases=["monthly recurring revenue"],
                           description="Monthly recurring revenue"),
            FieldDefinition("arr", "ARR", required=False,
                           aliases=["annual recurring revenue"],
                           description="Annual recurring revenue"),
            FieldDefinition("customer_count", "Customer Count", required=False,
                           aliases=["customers", "# customers", "number of customers", "logo count"],
                           description="Number of customers"),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return []

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Revenue ~ Units * Price (within 20%)",
                check=lambda df: _check_units_times_price(df),
                severity="warning",
            ),
            ValidationRule(
                name="ARR ~ MRR * 12 (within 10%)",
                check=lambda df: _check_arr_mrr(df),
                severity="warning",
            ),
            ValidationRule(
                name="Revenue should be non-negative",
                check=lambda df: (True, "") if "revenue" not in df.columns or (df["revenue"] >= 0).all()
                    else (True, "Warning: Some rows have negative revenue"),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_units_times_price(df: pd.DataFrame) -> tuple[bool, str]:
    """Check if revenue is within 20% of units_sold * unit_price."""
    if "units_sold" not in df.columns or "unit_price" not in df.columns or "revenue" not in df.columns:
        return True, ""
    try:
        mask = df["units_sold"].notna() & df["unit_price"].notna() & df["revenue"].notna()
        subset = df[mask]
        if subset.empty:
            return True, ""
        expected = subset["units_sold"] * subset["unit_price"]
        actual = subset["revenue"]
        pct_diff = ((actual - expected).abs() / expected.abs().replace(0, float("nan"))).dropna()
        if pct_diff.empty:
            return True, ""
        max_pct = pct_diff.max()
        if max_pct > 0.20:
            return True, f"Warning: Revenue differs from units * price by up to {max_pct:.0%} (discounts or adjustments likely)"
        return True, ""
    except Exception:
        return True, ""


def _check_arr_mrr(df: pd.DataFrame) -> tuple[bool, str]:
    """Check if ARR ~ MRR * 12 within 10%."""
    if "mrr" not in df.columns or "arr" not in df.columns:
        return True, ""
    try:
        mask = df["mrr"].notna() & df["arr"].notna()
        subset = df[mask]
        if subset.empty:
            return True, ""
        expected_arr = subset["mrr"] * 12
        actual_arr = subset["arr"]
        pct_diff = ((actual_arr - expected_arr).abs() / expected_arr.abs().replace(0, float("nan"))).dropna()
        if pct_diff.empty:
            return True, ""
        max_pct = pct_diff.max()
        if max_pct > 0.10:
            return True, f"Warning: ARR differs from MRR * 12 by up to {max_pct:.0%}"
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(RevenueDetailSchema())
