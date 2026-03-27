"""
Trial Balance / General Ledger schema definition.
"""

import pandas as pd
from core.schemas.base import DocumentSchema, FieldDefinition, DerivationRule, ValidationRule
from core.registry import DocumentTypeRegistry


class TrialBalanceSchema(DocumentSchema):

    @property
    def doc_type_id(self) -> str:
        return "trial_balance"

    @property
    def doc_type_name(self) -> str:
        return "Trial Balance / General Ledger"

    @property
    def classification_keywords(self) -> dict[str, int]:
        return {
            "trial balance": 15, "general ledger": 15, "chart of accounts": 12,
            "debit": 10, "credit": 10, "account number": 8, "account name": 8,
            "gl": 10, "ledger": 8, "journal": 6, "dr": 4, "cr": 4,
        }

    @property
    def fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("account_number", "Account Number", required=False,
                           is_financial=False, is_temporal=False,
                           aliases=["acct no", "acct #", "account #", "gl account", "account code"],
                           description="General ledger account number"),
            FieldDefinition("account_name", "Account Name", required=True,
                           is_financial=False, is_temporal=False,
                           aliases=["account description", "description", "account", "gl description", "account title"],
                           description="General ledger account name/description"),
            FieldDefinition("account_type", "Account Type", required=False,
                           is_financial=False,
                           aliases=["type", "category", "class", "account class"],
                           description="Account type or classification"),
            FieldDefinition("debit", "Debit", required=True,
                           aliases=["debit balance", "dr", "debit amount"],
                           description="Debit balance"),
            FieldDefinition("credit", "Credit", required=True,
                           aliases=["credit balance", "cr", "credit amount"],
                           description="Credit balance"),
            FieldDefinition("net_balance", "Net Balance", required=False,
                           aliases=["balance", "net", "net amount"],
                           description="Net balance (debit - credit). Can be derived."),
            FieldDefinition("department", "Department", required=False,
                           is_financial=False,
                           aliases=["dept", "cost center", "division", "segment"],
                           description="Department or cost center"),
            FieldDefinition("period", "Period", required=False,
                           is_financial=False, is_temporal=True,
                           aliases=["date", "month", "as of"],
                           description="Reporting period or date"),
        ]

    @property
    def temporal_field(self) -> str:
        return "period"

    @property
    def derivations(self) -> list[DerivationRule]:
        return [
            DerivationRule(
                target="net_balance",
                dependencies=["debit", "credit"],
                formula=lambda row: row["debit"] - row["credit"],
                description="debit - credit",
            ),
        ]

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return [
            ValidationRule(
                name="Total debits == Total credits",
                check=lambda df: _check_trial_balance(df),
                severity="error",
            ),
        ]

    # Uses default build_normalization_prompt() from base class


def _check_trial_balance(df: pd.DataFrame) -> tuple[bool, str]:
    """Check that total debits equal total credits within $1 tolerance."""
    if "debit" not in df.columns or "credit" not in df.columns:
        return True, ""
    try:
        total_debit = df["debit"].sum()
        total_credit = df["credit"].sum()
        diff = abs(total_debit - total_credit)
        if diff > 1.0:
            return False, f"Trial balance does not balance. Total debits: ${total_debit:,.2f}, Total credits: ${total_credit:,.2f}, Difference: ${diff:,.2f}"
        return True, ""
    except Exception:
        return True, ""


# Register
DocumentTypeRegistry.register(TrialBalanceSchema())
