"""
Value creation agent output types.

SizedInitiative is the atomic output — every recommendation has dollar sizing.
ValueCreationPlan is the complete agent output.
"""

from dataclasses import dataclass, field
from modeling.types import Initiative


@dataclass
class SizedInitiative:
    """One specific, dollar-sized value creation opportunity."""
    name: str
    category: str              # Revenue | Margin | AI Automation | AI Product | Working Capital
    description: str
    ebitda_impact_annual: float
    implementation_cost: float = 0.0
    timeline_months: int = 6
    confidence: str = "Medium"  # High | Medium | Low
    specific_tools: list[str] = field(default_factory=list)
    research_source: str = ""

    def to_initiative(self, start_period: str = "") -> Initiative:
        """Convert to modeling Initiative for the projection engine."""
        conf_map = {"High": 80.0, "Medium": 50.0, "Low": 25.0}
        return Initiative(
            name=self.name,
            ebitda_impact_run_rate=self.ebitda_impact_annual / 12,
            implementation_cost=self.implementation_cost,
            start_period=start_period,
            ramp_months=max(1, self.timeline_months // 2),
            confidence_pct=conf_map.get(self.confidence, 50.0),
        )


@dataclass
class ValueCreationPlan:
    """Complete output of the value creation agent system."""
    company_name: str = ""
    generated_at: str = ""

    # Agent 1: Financial
    financial_initiatives: list[SizedInitiative] = field(default_factory=list)

    # Agent 2: AI Transformation
    ai_automation_opportunities: list[SizedInitiative] = field(default_factory=list)
    ai_product_recommendations: list[str] = field(default_factory=list)
    ai_disruption_risks: list[str] = field(default_factory=list)
    proprietary_ai_opportunities: list[str] = field(default_factory=list)

    # Agent 3: Strategic
    strategic_priorities: list[str] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)
    exit_readiness_notes: str = ""

    # Synthesis
    executive_summary: str = ""
    prioritized_plan: list[SizedInitiative] = field(default_factory=list)
    total_ebitda_opportunity: float = 0.0
    conflicts_resolved: list[str] = field(default_factory=list)
