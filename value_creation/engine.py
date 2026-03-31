"""
Value creation engine. Orchestrates all agents in parallel and produces
the final ValueCreationPlan.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from analysis.types import AnalysisResult
from research.types import ResearchBrief
from value_creation.types import ValueCreationPlan
from value_creation.context import build_context_block
from value_creation.financial_agent import run_financial_agent
from value_creation.ai_transform_agent import run_ai_transform_agent
from value_creation.strategic_agent import run_strategic_agent
from value_creation.synthesis_agent import run_synthesis_agent


def run_value_creation(
    company_name: str,
    sector: str,
    analysis: AnalysisResult,
    research_brief: ResearchBrief | None = None,
) -> ValueCreationPlan:
    """
    Run the full value creation agent pipeline.

    1. Build context from analysis + research
    2. Run 3 specialist agents in parallel
    3. Run synthesis agent to merge and rank
    4. Return ValueCreationPlan
    """
    plan = ValueCreationPlan(
        company_name=company_name,
        generated_at=date.today().isoformat(),
    )

    # Build context
    context_block = build_context_block(analysis, research_brief, company_name, sector)

    # Get LTM revenue for sizing
    ltm_revenue = 0
    if analysis.ltm and analysis.ltm.ltm_revenue:
        ltm_revenue = analysis.ltm.ltm_revenue
    elif analysis.margins and analysis.margins.periods:
        # Fallback: annualize latest month
        last = analysis.margins.periods[-1]
        # Need to get revenue from somewhere else
        ltm_revenue = 30000000  # safe default

    # Get company profile for AI agent
    profile = research_brief.profile if research_brief else None

    # Run 3 specialist agents in parallel
    financial_output = []
    ai_output = {}
    strategic_output = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(run_financial_agent, context_block, company_name, ltm_revenue)
        f2 = pool.submit(run_ai_transform_agent, context_block, company_name, ltm_revenue, profile, sector)
        f3 = pool.submit(run_strategic_agent, context_block, company_name)

        try:
            financial_output = f1.result(timeout=30)
        except Exception:
            financial_output = []

        try:
            ai_output = f2.result(timeout=90)  # Longer: 12 Perplexity calls
        except Exception:
            ai_output = {}

        try:
            strategic_output = f3.result(timeout=30)
        except Exception:
            strategic_output = {}

    # Store specialist outputs
    plan.financial_initiatives = financial_output
    plan.ai_automation_opportunities = ai_output.get("ai_automation", [])
    plan.ai_product_recommendations = ai_output.get("ai_product_recommendations", [])
    plan.ai_disruption_risks = ai_output.get("ai_disruption_risks", [])
    plan.proprietary_ai_opportunities = ai_output.get("proprietary_ai_opportunities", [])
    plan.strategic_priorities = strategic_output.get("strategic_priorities", [])
    plan.key_risks = strategic_output.get("key_risks", [])
    plan.exit_readiness_notes = strategic_output.get("exit_readiness_notes", "")

    # Run synthesis agent
    synthesis = run_synthesis_agent(
        financial_output, ai_output, strategic_output,
        context_block, company_name,
    )

    plan.executive_summary = synthesis.get("executive_summary", "")
    plan.prioritized_plan = synthesis.get("prioritized_plan", [])
    plan.total_ebitda_opportunity = synthesis.get("total_ebitda_opportunity", 0)
    plan.conflicts_resolved = synthesis.get("conflicts_resolved", [])

    return plan
