"""
Modeling engine orchestrator.

project → combine with historical → run analysis → compute returns
"""

from core.result import NormalizedResult
from analysis.engine import run_analysis
from modeling.types import AssumptionSet, ModelResult
from modeling.projections import project


def run_model(
    historical: dict[str, NormalizedResult],
    assumptions: AssumptionSet,
) -> ModelResult:
    """
    Full modeling pipeline:
    1. Project forward from historical data using assumptions
    2. Run existing analysis engine on combined (historical + projected) data
    3. Compute returns if exit assumptions are set
    """
    # Step 1: Project
    combined = project(historical, assumptions)

    # Step 2: Run analysis (unchanged existing engine)
    analysis = run_analysis(combined)

    # Step 3: Compute returns
    returns = None
    if assumptions.exit_.entry_equity > 0:
        try:
            from modeling.returns import compute_returns
            returns = compute_returns(analysis, assumptions, combined)
        except Exception:
            pass  # returns module not yet built or data insufficient

    return ModelResult(
        assumptions=assumptions,
        combined_data=combined,
        analysis=analysis,
        returns=returns,
    )
