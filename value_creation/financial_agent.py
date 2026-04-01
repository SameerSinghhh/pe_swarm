"""
Agent 1: Financial Value Creation.

Analyzes financial data to find EBITDA improvement opportunities.
Sizes every recommendation in dollars using LTM revenue.
"""

import json
import os
import re
from dotenv import load_dotenv

from value_creation.types import SizedInitiative

load_dotenv()

SYSTEM_PROMPT = """You are a PE operating partner analyzing financial data to find EBITDA improvement opportunities.

RULES:
1. Every recommendation MUST have a dollar estimate. No hand-waving.
2. Use the company's actual LTM revenue of ${ltm_revenue} to size opportunities.
3. When margins are below peers, size the gap: (peer_median - company_margin) * LTM_revenue = annual opportunity.
4. When costs grow faster than revenue, quantify the excess growth.
5. For working capital: DSO improvement of X days = (X/365) * LTM_revenue in cash freed.
6. Be specific about WHAT to do, not just "improve margins."

ANALYSIS AREAS:
- Margin gaps vs peers (gross margin, EBITDA margin, each OpEx line)
- Cost lines growing faster than revenue
- Working capital optimization (DSO reduction, DPO extension)
- Revenue concentration risk
- Pricing power (if revenue growing by volume not price)
- Overhead leverage (G&A scaling)

Return ONLY valid JSON with this exact structure. No markdown, no code fences, no text before or after:
{
  "initiatives": [
    {
      "name": "Short name",
      "category": "Revenue or Margin or Working Capital",
      "description": "2-3 sentences explaining what to do and why with specific numbers",
      "ebitda_impact_annual": 123456,
      "implementation_cost": 12345,
      "timeline_months": 6,
      "confidence": "High or Medium or Low",
      "specific_tools": [],
      "research_source": "Financial analysis"
    }
  ]
}"""


def _clean_json_text(text: str) -> str:
    """Aggressively clean text to extract valid JSON."""
    # Strip markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    # Find the JSON object boundaries
    start = text.find("{")
    if start == -1:
        return text

    # Find matching closing brace
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    return text[start:end]


def run_financial_agent(context_block: str, company_name: str, ltm_revenue: float) -> list[SizedInitiative]:
    """Run the financial value creation agent."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return []

    # Clean the context block of problematic chars
    clean_context = re.sub(r'[{}]', '', context_block)

    prompt = SYSTEM_PROMPT.replace("{ltm_revenue}", f"{ltm_revenue:,.0f}")

    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=prompt,
            messages=[{"role": "user", "content": clean_context}],
        )

        text = response.content[0].text.strip()
        text = _clean_json_text(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Retry: ask Claude to fix the JSON
            retry = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": "Return ONLY valid JSON. " + prompt.split("Return ONLY")[1] if "Return ONLY" in prompt else prompt},
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": "That JSON was invalid. Please return ONLY the corrected JSON object, nothing else."},
                ],
            )
            retry_text = _clean_json_text(retry.content[0].text.strip())
            data = json.loads(retry_text)

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

    except Exception:
        return []
