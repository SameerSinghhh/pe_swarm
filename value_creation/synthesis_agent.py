"""
Synthesis Agent: The Moderator.

Takes outputs from all three specialist agents, resolves conflicts,
deduplicates, ranks by impact/effort, and produces the final plan.
"""

import json
import os
import re
from dotenv import load_dotenv

from value_creation.types import SizedInitiative

load_dotenv()


def run_synthesis_agent(
    financial_output: list,
    ai_output: dict,
    strategic_output: dict,
    context_block: str,
    company_name: str,
) -> dict:
    """
    Synthesize all agent outputs into a final value creation plan.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return _fallback_synthesis(financial_output, ai_output, strategic_output)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return _fallback_synthesis(financial_output, ai_output, strategic_output)

    # Serialize agent outputs
    fin_json = json.dumps([{
        "name": i.name, "category": i.category, "description": i.description,
        "ebitda_impact_annual": i.ebitda_impact_annual, "implementation_cost": i.implementation_cost,
        "timeline_months": i.timeline_months, "confidence": i.confidence,
        "specific_tools": i.specific_tools,
    } for i in financial_output], indent=2) if financial_output else "[]"

    ai_auto_json = json.dumps([{
        "name": i.name, "category": i.category, "description": i.description,
        "ebitda_impact_annual": i.ebitda_impact_annual, "implementation_cost": i.implementation_cost,
        "timeline_months": i.timeline_months, "confidence": i.confidence,
        "specific_tools": i.specific_tools,
    } for i in ai_output.get("ai_automation", [])], indent=2) if ai_output else "[]"

    system_prompt = f"""You are a senior PE operating partner synthesizing recommendations from three specialist analysts for {company_name}.

1. RESOLVE CONFLICTS: If agents disagree, explain the tradeoff and decide.
2. DEDUPLICATE: Merge similar recommendations.
3. RANK ALL INITIATIVES by: (ebitda_impact × confidence_factor) / (implementation_cost + timeline × 5000)
   Confidence factors: High=0.8, Medium=0.5, Low=0.25
4. WRITE EXECUTIVE SUMMARY: 2-3 paragraphs. Lead with total opportunity. Top 3 initiatives. Biggest risk. Direct, no fluff.

FINANCIAL AGENT (margin/cost/WC opportunities):
{fin_json}

AI TRANSFORMATION AGENT (automation/product/threats):
{ai_auto_json}

AI Product Recommendations: {json.dumps(ai_output.get('ai_product_recommendations', []))}
AI Disruption Risks: {json.dumps(ai_output.get('ai_disruption_risks', []))}
Proprietary AI: {json.dumps(ai_output.get('proprietary_ai_opportunities', []))}

STRATEGIC AGENT:
Priorities: {json.dumps(strategic_output.get('strategic_priorities', []))}
Risks: {json.dumps(strategic_output.get('key_risks', []))}

Return ONLY valid JSON:
{{
  "executive_summary": "2-3 paragraph narrative",
  "prioritized_plan": [
    {{
      "name": "...", "category": "...", "description": "...",
      "ebitda_impact_annual": 12345, "implementation_cost": 5000,
      "timeline_months": 6, "confidence": "High|Medium|Low",
      "specific_tools": [], "research_source": "..."
    }}
  ],
  "conflicts_resolved": ["Description of each conflict and resolution"],
  "total_ebitda_opportunity": 123456
}}"""

    try:
        client = Anthropic()
        clean_context = re.sub(r'[{}]', '', context_block)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": clean_context}],
        )

        text = response.content[0].text.strip()
        from value_creation.financial_agent import _clean_json_text
        text = _clean_json_text(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return _fallback_synthesis(financial_output, ai_output, strategic_output)

        # Parse prioritized plan
        plan = []
        for item in data.get("prioritized_plan", []):
            plan.append(SizedInitiative(
                name=item.get("name", ""),
                category=item.get("category", ""),
                description=item.get("description", ""),
                ebitda_impact_annual=float(item.get("ebitda_impact_annual", 0)),
                implementation_cost=float(item.get("implementation_cost", 0)),
                timeline_months=int(item.get("timeline_months", 6)),
                confidence=item.get("confidence", "Medium"),
                specific_tools=item.get("specific_tools", []),
                research_source=item.get("research_source", ""),
            ))

        return {
            "executive_summary": data.get("executive_summary", ""),
            "prioritized_plan": plan,
            "conflicts_resolved": data.get("conflicts_resolved", []),
            "total_ebitda_opportunity": float(data.get("total_ebitda_opportunity", 0)),
        }

    except Exception:
        return _fallback_synthesis(financial_output, ai_output, strategic_output)


def _fallback_synthesis(financial_output, ai_output, strategic_output) -> dict:
    """Simple fallback when Claude is unavailable: just merge and sort."""
    all_initiatives = list(financial_output or [])
    all_initiatives.extend(ai_output.get("ai_automation", []) if ai_output else [])

    # Sort by EBITDA impact descending
    all_initiatives.sort(key=lambda x: x.ebitda_impact_annual, reverse=True)
    total = sum(i.ebitda_impact_annual for i in all_initiatives)

    return {
        "executive_summary": f"Identified {len(all_initiatives)} initiatives with total annual EBITDA opportunity of ${total:,.0f}.",
        "prioritized_plan": all_initiatives,
        "conflicts_resolved": [],
        "total_ebitda_opportunity": total,
    }
