"""
Cash Flow Statement schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class CashFlowSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "cash_flow"

    @property
    def doc_type_name(self) -> str:
        return "Cash Flow Statement"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "cash flow": 15, "cash flow statement": 15,
            "operating activities": 12, "investing activities": 12, "financing activities": 12,
            "capex": 8, "capital expenditure": 8,
            "free cash flow": 10, "fcf": 10,
            "net change in cash": 8, "beginning cash": 6, "ending cash": 6,
            "depreciation": 4,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "month", "period ending"],
                           description="Time period (month/quarter/year)"),
            FieldDefinition("net_income", "Net Income", required=False,
                           aliases=["net profit", "net earnings", "profit after tax"],
                           description="Net income / net profit"),
            FieldDefinition("depreciation_amortization", "Depreciation & Amortization", required=False,
                           aliases=["d&a", "depreciation", "amortization", "depreciation and amortization"],
                           description="Depreciation and amortization add-back"),
            FieldDefinition("changes_in_working_capital", "Changes in Working Capital", required=False,
                           aliases=["working capital changes", "change in working capital", "wc changes"],
                           description="Net change in working capital"),
            FieldDefinition("other_operating", "Other Operating", required=False,
                           aliases=["other operating activities", "other adjustments", "non-cash adjustments"],
                           description="Other operating cash flow adjustments"),
            FieldDefinition("cash_from_operations", "Cash from Operations", required=True,
                           aliases=["operating cash flow", "cfo", "net cash from operations",
                                    "cash from operating activities", "net cash provided by operating"],
                           description="Net cash from operating activities"),
            FieldDefinition("capex", "Capital Expenditures", required=False,
                           aliases=["capital expenditures", "purchases of property", "capital spending", "pp&e purchases"],
                           description="Capital expenditures (typically negative)"),
            FieldDefinition("acquisitions", "Acquisitions", required=False,
                           aliases=["acquisition spend", "business acquisitions"],
                           description="Cash spent on acquisitions"),
            FieldDefinition("other_investing", "Other Investing", required=False,
                           aliases=["other investing activities", "other investing"],
                           description="Other investing activities"),
            FieldDefinition("cash_from_investing", "Cash from Investing", required=True,
                           aliases=["investing cash flow", "cfi", "net cash from investing",
                                    "cash from investing activities"],
                           description="Net cash from investing activities"),
            FieldDefinition("debt_issued", "Debt Issued", required=False,
                           aliases=["proceeds from debt", "borrowings", "debt proceeds"],
                           description="Proceeds from debt issuance"),
            FieldDefinition("debt_repaid", "Debt Repaid", required=False,
                           aliases=["debt repayment", "principal payments", "debt paydown"],
                           description="Debt repayment"),
            FieldDefinition("equity_issued", "Equity Issued", required=False,
                           aliases=["equity issuance", "stock issuance", "proceeds from equity"],
                           description="Proceeds from equity issuance"),
            FieldDefinition("dividends_paid", "Dividends Paid", required=False,
                           aliases=["dividend payments", "dividends", "distributions"],
                           description="Dividends paid to shareholders"),
            FieldDefinition("other_financing", "Other Financing", required=False,
                           aliases=["other financing activities"],
                           description="Other financing activities"),
            FieldDefinition("cash_from_financing", "Cash from Financing", required=True,
                           aliases=["financing cash flow", "cff", "net cash from financing",
                                    "cash from financing activities"],
                           description="Net cash from financing activities"),
            FieldDefinition("net_change_in_cash", "Net Change in Cash", required=True,
                           aliases=["net change", "change in cash", "net increase in cash", "net cash change"],
                           description="Net change in cash. Can be derived."),
            FieldDefinition("beginning_cash", "Beginning Cash", required=False,
                           aliases=["beginning balance", "opening cash", "cash at beginning"],
                           description="Cash balance at beginning of period"),
            FieldDefinition("ending_cash", "Ending Cash", required=False,
                           aliases=["ending balance", "closing cash", "cash at end"],
                           description="Cash balance at end of period. Can be derived."),
            FieldDefinition("free_cash_flow", "Free Cash Flow", required=False,
                           aliases=["fcf", "free cash flow"],
                           description="Free cash flow. Can be derived."),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="net_change_in_cash",
                dependencies=["cash_from_operations", "cash_from_investing", "cash_from_financing"],
                formula=lambda row: (
                    row["cash_from_operations"] + row["cash_from_investing"] + row["cash_from_financing"]
                ),
                description="cash_from_operations + cash_from_investing + cash_from_financing",
            ),
            DerivationRule(
                target="ending_cash",
                dependencies=["beginning_cash", "net_change_in_cash"],
                formula=lambda row: row["beginning_cash"] + row["net_change_in_cash"],
                description="beginning_cash + net_change_in_cash",
            ),
            DerivationRule(
                target="free_cash_flow",
                dependencies=["cash_from_operations"],
                formula=lambda row: row["cash_from_operations"] + row.get("capex", 0),
                description="cash_from_operations + capex (capex is typically negative)",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Net change in cash == ops + investing + financing",
                check=lambda df: _check_cash_sum(df),
                severity="warning",
            ),
            ValidationRule(
                name="Ending cash == beginning cash + net change",
                check=lambda df: _check_ending_cash(df),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_cash_sum(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that net change in cash equals sum of three sections within 1% tolerance."""
    required = ["net_change_in_cash", "cash_from_operations", "cash_from_investing", "cash_from_financing"]
    if not all(c in df.columns for c in required):
        return True, ""
    try:
        expected = df["cash_from_operations"] + df["cash_from_investing"] + df["cash_from_financing"]
        actual = df["net_change_in_cash"]
        diff = (actual - expected).abs()
        threshold = actual.abs() * 0.01
        threshold = threshold.clip(lower=1.0)
        if (diff > threshold).any():
            max_diff = diff.max()
            return True, f"Warning: Net change in cash off by up to ${max_diff:,.0f} from sum of sections."
        return True, ""
    except Exception:
        return True, ""


def _check_ending_cash(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that ending cash equals beginning cash plus net change within 1% tolerance."""
    required = ["ending_cash", "beginning_cash", "net_change_in_cash"]
    if not all(c in df.columns for c in required):
        return True, ""
    try:
        expected = df["beginning_cash"] + df["net_change_in_cash"]
        actual = df["ending_cash"]
        diff = (actual - expected).abs()
        threshold = actual.abs() * 0.01
        threshold = threshold.clip(lower=1.0)
        if (diff > threshold).any():
            max_diff = diff.max()
            return True, f"Warning: Ending cash off by up to ${max_diff:,.0f} from beginning + net change."
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(CashFlowSchema())
