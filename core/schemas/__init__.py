# Import all schemas to trigger registration.
# This must be called AFTER registry.py is fully loaded.

def _register_all():
    from core.schemas.income_statement import IncomeStatementSchema  # noqa: F401
    from core.schemas.balance_sheet import BalanceSheetSchema  # noqa: F401
    from core.schemas.cash_flow import CashFlowSchema  # noqa: F401
    from core.schemas.trial_balance import TrialBalanceSchema  # noqa: F401
    from core.schemas.working_capital import WorkingCapitalSchema  # noqa: F401
    from core.schemas.revenue_detail import RevenueDetailSchema  # noqa: F401
    from core.schemas.cost_detail import CostDetailSchema  # noqa: F401
    from core.schemas.kpi_operational import KpiOperationalSchema  # noqa: F401


_register_all()
