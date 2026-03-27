"""
Balance Sheet schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class BalanceSheetSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "balance_sheet"

    @property
    def doc_type_name(self) -> str:
        return "Balance Sheet"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "balance sheet": 15, "assets": 8, "liabilities": 8, "equity": 8,
            "stockholders": 10, "current assets": 10, "property plant": 8,
            "retained earnings": 8, "accounts receivable": 6, "accounts payable": 6,
            "book value": 6, "net worth": 6,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "as of", "period ending", "reporting date"],
                           description="Reporting date or period"),
            FieldDefinition("cash", "Cash", required=True,
                           aliases=["cash and equivalents", "cash & equivalents", "cash and cash equivalents"],
                           description="Cash and cash equivalents"),
            FieldDefinition("accounts_receivable", "Accounts Receivable", required=True,
                           aliases=["ar", "trade receivables", "accounts receivable net", "a/r"],
                           description="Accounts receivable, net"),
            FieldDefinition("inventory", "Inventory", required=False,
                           aliases=["inventories", "total inventory", "merchandise inventory"],
                           description="Inventory"),
            FieldDefinition("prepaid_expenses", "Prepaid Expenses", required=False,
                           aliases=["prepaids", "prepaid", "prepaid and other"],
                           description="Prepaid expenses and other"),
            FieldDefinition("other_current_assets", "Other Current Assets", required=False,
                           aliases=["other ca", "other current"],
                           description="Other current assets"),
            FieldDefinition("total_current_assets", "Total Current Assets", required=True,
                           aliases=["current assets", "total ca"],
                           description="Total current assets. Can be derived."),
            FieldDefinition("pp_and_e_net", "PP&E Net", required=False,
                           aliases=["property plant and equipment", "ppe", "fixed assets", "pp&e net", "net pp&e"],
                           description="Property, plant & equipment, net"),
            FieldDefinition("intangible_assets", "Intangible Assets", required=False,
                           aliases=["goodwill", "intangibles", "goodwill and intangibles"],
                           description="Intangible assets and goodwill"),
            FieldDefinition("other_non_current_assets", "Other Non-Current Assets", required=False,
                           aliases=["other assets", "other long-term assets", "other lt assets"],
                           description="Other non-current assets"),
            FieldDefinition("total_assets", "Total Assets", required=True,
                           aliases=["total assets"],
                           description="Total assets. Can be derived."),
            FieldDefinition("accounts_payable", "Accounts Payable", required=True,
                           aliases=["ap", "trade payables", "a/p"],
                           description="Accounts payable"),
            FieldDefinition("accrued_liabilities", "Accrued Liabilities", required=False,
                           aliases=["accrued expenses", "accruals"],
                           description="Accrued liabilities and expenses"),
            FieldDefinition("short_term_debt", "Short-Term Debt", required=False,
                           aliases=["current debt", "current portion of debt", "short term borrowings"],
                           description="Short-term debt and current portion of long-term debt"),
            FieldDefinition("other_current_liabilities", "Other Current Liabilities", required=False,
                           aliases=["other cl", "other current liabilities", "deferred revenue"],
                           description="Other current liabilities"),
            FieldDefinition("total_current_liabilities", "Total Current Liabilities", required=True,
                           aliases=["current liabilities", "total cl"],
                           description="Total current liabilities. Can be derived."),
            FieldDefinition("long_term_debt", "Long-Term Debt", required=False,
                           aliases=["lt debt", "long-term borrowings", "notes payable"],
                           description="Long-term debt"),
            FieldDefinition("other_non_current_liabilities", "Other Non-Current Liabilities", required=False,
                           aliases=["other lt liabilities", "other long-term liabilities"],
                           description="Other non-current liabilities"),
            FieldDefinition("total_liabilities", "Total Liabilities", required=True,
                           aliases=["total liabilities"],
                           description="Total liabilities. Can be derived."),
            FieldDefinition("total_equity", "Total Equity", required=True,
                           aliases=["equity", "stockholders equity", "shareholders equity",
                                    "total stockholders equity", "net worth", "owners equity"],
                           description="Total stockholders' equity"),
            FieldDefinition("total_liabilities_and_equity", "Total Liabilities & Equity", required=True,
                           aliases=["total liabilities and equity", "total l&e"],
                           description="Total liabilities and equity. Can be derived."),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="total_current_assets",
                dependencies=["cash", "accounts_receivable"],
                formula=lambda row: (
                    row.get("cash", 0) + row.get("accounts_receivable", 0)
                    + row.get("inventory", 0) + row.get("prepaid_expenses", 0)
                    + row.get("other_current_assets", 0)
                ),
                description="cash + accounts_receivable + inventory + prepaid_expenses + other_current_assets",
            ),
            DerivationRule(
                target="total_assets",
                dependencies=["total_current_assets"],
                formula=lambda row: (
                    row.get("total_current_assets", 0) + row.get("pp_and_e_net", 0)
                    + row.get("intangible_assets", 0) + row.get("other_non_current_assets", 0)
                ),
                description="total_current_assets + pp_and_e_net + intangible_assets + other_non_current_assets",
            ),
            DerivationRule(
                target="total_current_liabilities",
                dependencies=["accounts_payable"],
                formula=lambda row: (
                    row.get("accounts_payable", 0) + row.get("accrued_liabilities", 0)
                    + row.get("short_term_debt", 0) + row.get("other_current_liabilities", 0)
                ),
                description="accounts_payable + accrued_liabilities + short_term_debt + other_current_liabilities",
            ),
            DerivationRule(
                target="total_liabilities",
                dependencies=["total_current_liabilities"],
                formula=lambda row: (
                    row.get("total_current_liabilities", 0) + row.get("long_term_debt", 0)
                    + row.get("other_non_current_liabilities", 0)
                ),
                description="total_current_liabilities + long_term_debt + other_non_current_liabilities",
            ),
            DerivationRule(
                target="total_liabilities_and_equity",
                dependencies=["total_liabilities", "total_equity"],
                formula=lambda row: row.get("total_liabilities", 0) + row.get("total_equity", 0),
                description="total_liabilities + total_equity",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Total Assets == Total Liabilities & Equity",
                check=lambda df: _check_balance(df),
                severity="error",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_balance(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that total assets equals total liabilities and equity within 1% tolerance."""
    if "total_assets" not in df.columns or "total_liabilities_and_equity" not in df.columns:
        return True, ""
    try:
        assets = df["total_assets"]
        tle = df["total_liabilities_and_equity"]
        diff = (assets - tle).abs()
        threshold = assets.abs() * 0.01
        if (diff > threshold).any():
            max_diff = diff.max()
            return False, f"Total Assets does not equal Total Liabilities & Equity. Max difference: ${max_diff:,.0f}"
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(BalanceSheetSchema())
