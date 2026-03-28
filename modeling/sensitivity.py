"""
2-way sensitivity tables.

Vary two assumptions simultaneously, compute a result metric for each combination.
Brute-force approach — runs full projection for each cell. Fast enough for typical grids.
"""

import copy

import pandas as pd

from core.result import NormalizedResult
from modeling.types import AssumptionSet
from modeling.engine import run_model


def sensitivity_table(
    historical: dict[str, NormalizedResult],
    base_assumptions: AssumptionSet,
    row_param: str,         # dot-path e.g. "revenue.growth_rate_pct"
    row_values: list[float],
    col_param: str,         # dot-path e.g. "exit_.exit_multiple"
    col_values: list[float],
    output_metric: str = "moic",  # "moic" | "irr" | "exit_ebitda" | "exit_equity" | "ltm_ebitda"
) -> pd.DataFrame:
    """
    Compute a 2-way sensitivity table.

    Returns DataFrame with row_values as index, col_values as columns.
    Each cell contains the output_metric value.
    """
    results = {}

    for rv in row_values:
        for cv in col_values:
            # Deep copy assumptions
            a = copy.deepcopy(base_assumptions)
            _set_nested_attr(a, row_param, rv)
            _set_nested_attr(a, col_param, cv)

            # Run model
            model = run_model(historical, a)

            # Extract metric
            val = _extract_metric(model, output_metric)
            results[(rv, cv)] = val

    # Build DataFrame
    data = {}
    for cv in col_values:
        col_label = f"{cv}"
        data[col_label] = [results.get((rv, cv)) for rv in row_values]

    df = pd.DataFrame(data, index=[f"{rv}" for rv in row_values])
    df.index.name = row_param.split(".")[-1]
    df.columns.name = col_param.split(".")[-1]

    return df


def _set_nested_attr(obj, dot_path: str, value):
    """Set a nested attribute using dot notation. e.g., 'revenue.growth_rate_pct' """
    parts = dot_path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


def _extract_metric(model, metric: str):
    """Extract a metric from a ModelResult."""
    if model.returns:
        r = model.returns
        if metric == "moic":
            return r.moic
        elif metric == "irr":
            return r.irr
        elif metric == "exit_ebitda":
            return r.exit_ebitda
        elif metric == "exit_equity":
            return r.exit_equity
        elif metric == "exit_ev":
            return r.exit_ev

    if model.analysis.ltm:
        ltm = model.analysis.ltm
        if metric == "ltm_ebitda":
            return ltm.ltm_ebitda
        elif metric == "ltm_revenue":
            return ltm.ltm_revenue
        elif metric == "rule_of_40":
            return ltm.rule_of_40

    return None
