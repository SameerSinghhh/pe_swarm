"""
Agent 1: Financial Value Creation.

Analyzes financial data to find EBITDA improvement opportunities.
Sizes every recommendation in dollars using LTM revenue.
"""

import json
import os
from dotenv import load_dotenv

from value_creation.types import SizedInitiative

load_dotenv()

SYSTEM_PROMPT = """You are a PE operating partner analyzing financial data to find EBITDA improvement opportunities.

RULES:
1. Every recommendation MUST have a dollar estimate. No hand-waving.
2. Use the company's actual LTM revenue of ${ltm_revenue} to size opportunities.
3. When margins are below peers, size the gap: (peer_median - company_margin) × LTM_revenue = annual opportunity.
4. When costs grow faster than revenue, quantify the excess growth.
5. For working capital: DSO improvement of X days = (X/365) × LTM_revenue in cash freed.
6. Be specific about WHAT to do, not just "improve margins."

ANALYSIS AREAS:
- Margin gaps vs peers (gross margin, EBITDA margin, each OpEx line)
- Cost lines growing faster than revenue
- Working capital optimization (DSO reduction, DPO extension)
- Revenue concentration risk
- Pricing power (if revenue growing by volume not price)
- Overhead leverage (G&A scaling)

Return ONLY valid JSON (no markdown, no code fences):
{{
  "initiatives": [
    {{
      "name": "Short name",
      "category": "Revenue|Margin|Working Capital",
      "description": "2-3 sentences: what to do, why, specific numbers",
      "ebitda_impact_annual": 123456,
      "implementation_cost": 12345,
      "timeline_months": 6,
      "confidence": "High|Medium|Low",
      "specific_tools": [],
      "research_source": "Financial analysis: [which metric]"
    }}
  ]
}}"""


def run_financial_agent(context_block: str, company_name: str, ltm_revenue: float) -> list[SizedInitiative]:
    """Run the financial value creation agent."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return []

    prompt = SYSTEM_PROMPT.replace("{ltm_revenue}", f"{ltm_revenue:,.0f}")

    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=prompt,
            messages=[{"role": "user", "content": context_block}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"): text = text[:-3].strip()

        data = json.loads(text)
        initiatives = []
        for item in data.get("initiatives", []):
            initiatives.append(SizedInitiative(
                name=item.get("name", ""),
                category=item.get("category", "Margin"),
                description=item.get("description", ""),
                ebitda_impact_annual=float(item.get("ebitda_impact_annual", 0)),
                implementation_cost=float(item.get("implementation_cost", 0)),
                timeline_months=int(item.get("timeline_months", 6)),
                confidence=item.get("confidence", "Medium"),
                specific_tools=item.get("specific_tools", []),
                research_source=item.get("research_source", ""),
            ))
        return initiatives

    except Exception as e:
        # Return error info so the engine can report it
        return [SizedInitiative(
            name=f"[Agent Error: {type(e).__name__}]",
            category="Error",
            description=str(e)[:200],
            ebitda_impact_annual=0,
        )]
