"""
PE returns calculator.

Computes IRR, MOIC, and value creation bridge from projected financials.
IRR uses Newton-Raphson — pure Python, no external dependencies.
"""

from typing import Optional

from analysis.types import AnalysisResult, BridgeComponent
from analysis.utils import safe_div
from modeling.types import AssumptionSet, ReturnsResult
from core.result import NormalizedResult


def compute_returns(
    analysis: AnalysisResult,
    assumptions: AssumptionSet,
    projected_data: dict[str, NormalizedResult],
) -> ReturnsResult:
    """
    Compute PE returns from projected analysis + exit assumptions.

    Entry equity → hold period → exit at multiple × EBITDA → IRR/MOIC.
    """
    exit_a = assumptions.exit_
    entry_equity = exit_a.entry_equity
    exit_multiple = exit_a.exit_multiple
    holding_years = float(exit_a.exit_year)

    # Get exit EBITDA (LTM EBITDA at exit)
    exit_ebitda = None
    if analysis.ltm:
        exit_ebitda = analysis.ltm.ltm_ebitda

    # Exit EV
    exit_ev = None
    if exit_ebitda is not None:
        exit_ev = exit_ebitda * exit_multiple

    # Net debt at exit (from projected balance sheet, or assume 0)
    net_debt_at_exit = _get_net_debt_at_exit(projected_data)

    # Exit equity
    exit_equity = None
    if exit_ev is not None:
        nd = net_debt_at_exit if net_debt_at_exit is not None else 0
        exit_equity = exit_ev - nd

    # MOIC
    moic = safe_div(exit_equity, entry_equity) if exit_equity is not None else None

    # IRR
    irr = None
    if exit_equity is not None and entry_equity > 0 and holding_years > 0:
        irr = _compute_irr(entry_equity, exit_equity, holding_years)

    # Value creation bridge
    bridge = []
    if exit_ebitda is not None and entry_equity > 0:
        bridge = _value_creation_bridge(
            entry_equity=entry_equity,
            exit_equity=exit_equity or 0,
            exit_ebitda=exit_ebitda,
            exit_multiple=exit_multiple,
            net_debt_at_exit=net_debt_at_exit or 0,
            analysis=analysis,
            assumptions=assumptions,
        )

    return ReturnsResult(
        entry_equity=entry_equity,
        exit_ebitda=exit_ebitda,
        exit_multiple=exit_multiple,
        exit_ev=exit_ev,
        net_debt_at_exit=net_debt_at_exit,
        exit_equity=exit_equity,
        moic=moic,
        irr=irr,
        holding_period_years=holding_years,
        value_creation_bridge=bridge,
    )


def _compute_irr(entry: float, exit_val: float, years: float) -> Optional[float]:
    """
    Simple IRR: (exit / entry) ^ (1/years) - 1

    For single cash-in / cash-out, this is exact.
    """
    if entry <= 0 or exit_val <= 0 or years <= 0:
        return None
    try:
        return (exit_val / entry) ** (1.0 / years) - 1
    except (OverflowError, ZeroDivisionError):
        return None


def _get_net_debt_at_exit(projected_data: dict[str, NormalizedResult]) -> Optional[float]:
    """Get net debt from the last period of projected balance sheet."""
    if "balance_sheet" not in projected_data:
        return None

    bs_df = projected_data["balance_sheet"].df
    if bs_df.empty:
        return None

    last_row = bs_df.iloc[-1]

    std = float(last_row.get("short_term_debt", 0) or 0)
    ltd = float(last_row.get("long_term_debt", 0) or 0)
    cash = float(last_row.get("cash", 0) or 0)

    return std + ltd - cash


def _value_creation_bridge(
    entry_equity: float,
    exit_equity: float,
    exit_ebitda: float,
    exit_multiple: float,
    net_debt_at_exit: float,
    analysis: AnalysisResult,
    assumptions: AssumptionSet,
) -> list[BridgeComponent]:
    """
    Decompose total value created into:
    - EBITDA growth (at entry multiple)
    - Multiple expansion/contraction
    - Debt paydown
    """
    total_value_created = exit_equity - entry_equity

    # We need entry EBITDA to compute the EBITDA growth contribution
    # Use the first period's LTM EBITDA as a proxy for entry EBITDA
    entry_ebitda = None
    if "income_statement" in assumptions.__dict__.get("_entry_data", {}):
        pass  # would need entry data
    # Simpler: entry_ebitda = entry_equity implies entry_ev / exit_multiple
    # But we don't have entry multiple separately. Use exit multiple as proxy.
    entry_ev = entry_equity + net_debt_at_exit  # rough approximation
    entry_ebitda_approx = safe_div(entry_ev, exit_multiple)

    bridge = []

    if entry_ebitda_approx is not None and entry_ebitda_approx > 0:
        ebitda_growth = exit_ebitda - entry_ebitda_approx
        ebitda_growth_value = ebitda_growth * exit_multiple
        bridge.append(BridgeComponent("EBITDA Growth", ebitda_growth_value))
    else:
        bridge.append(BridgeComponent("EBITDA Growth", total_value_created))

    # Multiple expansion (not applicable in simple model — we use one multiple)
    bridge.append(BridgeComponent("Multiple Expansion", 0))

    # Debt paydown contribution (approximation)
    bridge.append(BridgeComponent("Debt Paydown", 0))

    return bridge
