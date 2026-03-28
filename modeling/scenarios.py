"""
Scenario manager. Run and compare multiple assumption sets.
"""

import pandas as pd

from core.result import NormalizedResult
from modeling.types import AssumptionSet, ModelResult
from modeling.engine import run_model


class ScenarioManager:
    """Holds multiple scenarios and provides comparison methods."""

    def __init__(
        self,
        historical: dict[str, NormalizedResult],
        scenarios: dict[str, AssumptionSet] | None = None,
    ):
        self.historical = historical
        self.scenarios = scenarios or {}
        self._results: dict[str, ModelResult] = {}

    def add_scenario(self, assumptions: AssumptionSet):
        self.scenarios[assumptions.name] = assumptions

    def run_scenario(self, name: str) -> ModelResult:
        """Run one scenario and cache the result."""
        if name not in self.scenarios:
            raise ValueError(f"Scenario '{name}' not found")
        result = run_model(self.historical, self.scenarios[name])
        self._results[name] = result
        return result

    def run_all(self) -> dict[str, ModelResult]:
        """Run all scenarios."""
        for name in self.scenarios:
            self.run_scenario(name)
        return self._results

    def get_result(self, name: str) -> ModelResult | None:
        return self._results.get(name)

    def compare_metric(self, metric: str) -> pd.DataFrame:
        """
        Compare a metric across all scenarios.

        Supported metrics: exit_ebitda, exit_ev, exit_equity, moic, irr,
        ltm_revenue, ltm_ebitda, rule_of_40
        """
        rows = []
        for name, result in self._results.items():
            row = {"Scenario": name}

            if result.returns:
                r = result.returns
                row["Exit EBITDA"] = r.exit_ebitda
                row["Exit EV"] = r.exit_ev
                row["Exit Equity"] = r.exit_equity
                row["MOIC"] = r.moic
                row["IRR"] = r.irr

            if result.analysis.ltm:
                ltm = result.analysis.ltm
                row["LTM Revenue"] = ltm.ltm_revenue
                row["LTM EBITDA"] = ltm.ltm_ebitda
                row["LTM EBITDA Margin %"] = ltm.ltm_ebitda_margin_pct
                row["Rule of 40"] = ltm.rule_of_40

            rows.append(row)

        return pd.DataFrame(rows).set_index("Scenario") if rows else pd.DataFrame()
