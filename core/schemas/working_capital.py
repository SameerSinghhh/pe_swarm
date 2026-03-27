"""
Working Capital / AR-AP Aging schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class WorkingCapitalSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "working_capital"

    @property
    def doc_type_name(self) -> str:
        return "Working Capital / AR-AP Aging"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "aging": 15, "ar aging": 15, "ap aging": 15,
            "accounts receivable aging": 12, "accounts payable aging": 12,
            "working capital": 10, "dso": 8, "dpo": 8, "dio": 8,
            "days outstanding": 8, "30 days": 4, "60 days": 4, "90 days": 4,
            "120 days": 4, "past due": 6, "current": 3,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("period", "Period", required=True, is_financial=False, is_temporal=True,
                           aliases=["date", "as of", "month", "reporting date"],
                           description="Reporting date or period"),
            FieldDefinition("ar_current", "AR Current", required=False,
                           aliases=["0-30", "current", "0-30 days", "ar current"],
                           description="Accounts receivable current (0-30 days)"),
            FieldDefinition("ar_31_60", "AR 31-60", required=False,
                           aliases=["31-60", "31-60 days"],
                           description="Accounts receivable 31-60 days"),
            FieldDefinition("ar_61_90", "AR 61-90", required=False,
                           aliases=["61-90", "61-90 days"],
                           description="Accounts receivable 61-90 days"),
            FieldDefinition("ar_91_120", "AR 91-120", required=False,
                           aliases=["91-120", "91-120 days"],
                           description="Accounts receivable 91-120 days"),
            FieldDefinition("ar_over_120", "AR Over 120", required=False,
                           aliases=["120+", "over 120", "120+ days", "past due"],
                           description="Accounts receivable over 120 days"),
            FieldDefinition("ar_total", "AR Total", required=True,
                           aliases=["total ar", "total receivables", "accounts receivable",
                                    "total accounts receivable"],
                           description="Total accounts receivable. Can be derived."),
            FieldDefinition("ap_current", "AP Current", required=False,
                           aliases=["ap 0-30", "ap current"],
                           description="Accounts payable current (0-30 days)"),
            FieldDefinition("ap_31_60", "AP 31-60", required=False,
                           aliases=["ap 31-60"],
                           description="Accounts payable 31-60 days"),
            FieldDefinition("ap_61_90", "AP 61-90", required=False,
                           aliases=["ap 61-90"],
                           description="Accounts payable 61-90 days"),
            FieldDefinition("ap_over_90", "AP Over 90", required=False,
                           aliases=["ap 90+", "ap over 90"],
                           description="Accounts payable over 90 days"),
            FieldDefinition("ap_total", "AP Total", required=False,
                           aliases=["total ap", "total payables", "accounts payable",
                                    "total accounts payable"],
                           description="Total accounts payable. Can be derived."),
            FieldDefinition("inventory_raw", "Raw Materials Inventory", required=False,
                           aliases=["raw materials", "raw material inventory"],
                           description="Raw materials inventory"),
            FieldDefinition("inventory_wip", "Work in Progress", required=False,
                           aliases=["work in progress", "wip"],
                           description="Work in progress inventory"),
            FieldDefinition("inventory_finished", "Finished Goods", required=False,
                           aliases=["finished goods", "finished goods inventory"],
                           description="Finished goods inventory"),
            FieldDefinition("inventory_total", "Total Inventory", required=False,
                           aliases=["total inventory", "inventory"],
                           description="Total inventory. Can be derived."),
            FieldDefinition("dso", "DSO", required=False,
                           aliases=["days sales outstanding"],
                           description="Days sales outstanding"),
            FieldDefinition("dpo", "DPO", required=False,
                           aliases=["days payable outstanding"],
                           description="Days payable outstanding"),
            FieldDefinition("dio", "DIO", required=False,
                           aliases=["days inventory outstanding"],
                           description="Days inventory outstanding"),
        ]

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="ar_total",
                dependencies=["ar_current"],
                formula=lambda row: (
                    row.get("ar_current", 0) + row.get("ar_31_60", 0)
                    + row.get("ar_61_90", 0) + row.get("ar_91_120", 0)
                    + row.get("ar_over_120", 0)
                ),
                description="ar_current + ar_31_60 + ar_61_90 + ar_91_120 + ar_over_120",
            ),
            DerivationRule(
                target="ap_total",
                dependencies=["ap_current"],
                formula=lambda row: (
                    row.get("ap_current", 0) + row.get("ap_31_60", 0)
                    + row.get("ap_61_90", 0) + row.get("ap_over_90", 0)
                ),
                description="ap_current + ap_31_60 + ap_61_90 + ap_over_90",
            ),
            DerivationRule(
                target="inventory_total",
                dependencies=["inventory_raw"],
                formula=lambda row: (
                    row.get("inventory_raw", 0) + row.get("inventory_wip", 0)
                    + row.get("inventory_finished", 0)
                ),
                description="inventory_raw + inventory_wip + inventory_finished",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="AR total == sum of AR buckets",
                check=lambda df: _check_ar_total(df),
                severity="warning",
            ),
            ValidationRule(
                name="DSO between 0 and 365",
                check=lambda df: _check_dso_range(df),
                severity="warning",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_ar_total(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that AR total equals sum of AR aging buckets if all buckets are present."""
    buckets = ["ar_current", "ar_31_60", "ar_61_90", "ar_91_120", "ar_over_120"]
    if "ar_total" not in df.columns or not all(b in df.columns for b in buckets):
        return True, ""
    try:
        expected = sum(df[b] for b in buckets)
        actual = df["ar_total"]
        diff = (actual - expected).abs()
        threshold = actual.abs() * 0.01
        threshold = threshold.clip(lower=1.0)
        if (diff > threshold).any():
            max_diff = diff.max()
            return True, f"Warning: AR total off by up to ${max_diff:,.0f} from sum of aging buckets."
        return True, ""
    except Exception:
        return True, ""


def _check_dso_range(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that DSO is between 0 and 365."""
    if "dso" not in df.columns:
        return True, ""
    try:
        dso = df["dso"].dropna()
        if len(dso) == 0:
            return True, ""
        if (dso < 0).any() or (dso > 365).any():
            return True, "Warning: DSO values outside expected range of 0-365 days."
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(WorkingCapitalSchema())
