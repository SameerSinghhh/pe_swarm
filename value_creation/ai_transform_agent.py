"""
Agent 2: AI Transformation.

The most valuable and novel agent. Does DEEP internet research via Perplexity
(12 targeted queries) to find:
1. AI tools to automate each department
2. AI features to build into the product
3. AI-native competitors threatening the business
4. Proprietary AI opportunities
"""

import json
import os
import re
import time
from dotenv import load_dotenv

from value_creation.types import SizedInitiative
from research.types import CompanyProfile

load_dotenv()


def run_ai_transform_agent(
    context_block: str,
    company_name: str,
    ltm_revenue: float,
    profile: CompanyProfile | None = None,
    sector: str = "",
) -> dict:
    """
    Run the AI transformation agent.

    Phase 1: 12 Perplexity research queries (targeted by department + sub-sector)
    Phase 2: Claude synthesizes research into recommendations

    Returns dict with: ai_automation, ai_product_recommendations,
    ai_disruption_risks, proprietary_ai_opportunities
    """
    # Phase 1: Research
    research_results = _do_research(profile, sector)

    # Phase 2: Claude synthesis
    return _synthesize(context_block, company_name, ltm_revenue, research_results, profile, sector)


def _build_research_queries(profile: CompanyProfile | None, sector: str) -> list[str]:
    """Generate 12 targeted research queries."""
    sub_sector = profile.sub_sector if profile and profile.sub_sector else sector
    biz_model = profile.business_model if profile and profile.business_model else sub_sector

    return [
        # Department automation (6)
        "best AI tools accounts payable invoice automation pricing ROI 2025 2026",
        "best AI tools sales forecasting CRM pipeline management pricing ROI 2025 2026",
        "best AI tools customer support chatbot ticket deflection pricing ROI 2025 2026",
        "best AI tools HR recruiting onboarding automation pricing ROI 2025 2026",
        "best AI tools FP&A financial planning budgeting automation pricing ROI 2025 2026",
        "best AI tools marketing content generation SEO automation pricing ROI 2025 2026",
        # Product AI (2)
        f"AI features in {sub_sector} software products 2025 2026 what customers expect",
        f"how {sub_sector} companies adding AI copilot features to product 2025 2026",
        # Threats (2)
        f"{sub_sector} AI-native startups disrupting incumbents 2025 2026",
        f"AI disruption risks for {biz_model} companies automation replacing 2025 2026",
        # Proprietary AI (2)
        f"how {sub_sector} companies use proprietary AI models grow revenue competitive advantage",
        f"{sub_sector} companies building custom AI differentiation examples 2025 2026",
    ]


def _do_research(profile: CompanyProfile | None, sector: str) -> str:
    """Run all 12 Perplexity queries and concatenate results."""
    from research.perplexity import ai_search

    queries = _build_research_queries(profile, sector)
    sections = []

    import re
    for i, query in enumerate(queries):
        try:
            result = ai_search(query)
            if result:
                # Clean problematic chars that break JSON in Claude's response
                clean = re.sub(r'\[\d+\]', '', result)
                clean = re.sub(r'<[^>]+>', '', clean)
                clean = re.sub(r'\$[^$]*\$', '', clean)
                clean = re.sub(r'[{}]', '', clean)
                sections.append(f"--- RESEARCH {i+1}: {query[:60]} ---\n{clean[:800]}")
            time.sleep(0.3)
        except Exception:
            continue

    return "\n\n".join(sections)


def _synthesize(
    context_block: str,
    company_name: str,
    ltm_revenue: float,
    research_results: str,
    profile: CompanyProfile | None,
    sector: str,
) -> dict:
    """Claude synthesizes research into structured recommendations."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return {}

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return {}

    system_prompt = f"""You are an AI transformation strategist for PE-backed companies. You have deep knowledge of AI tools and how they create value.

You have been given:
1. Financial data for {company_name} (LTM revenue: ${ltm_revenue:,.0f})
2. Detailed research on AI tools, features, and competitive threats

DELIVERABLE 1: AI AUTOMATION OPPORTUNITIES
For each relevant department, name the SPECIFIC tool, its pricing, and calculate ROI:
- Hours saved × hourly cost - tool cost = net savings
- Typical employee cost: $6K-8K/month for ops, $12K-15K/month for engineering

DELIVERABLE 2: AI PRODUCT RECOMMENDATIONS
What AI features should {company_name} build? Name competitors who already have similar.

DELIVERABLE 3: AI DISRUPTION RISKS
Which AI-native competitors or trends threaten this business? Be specific.

DELIVERABLE 4: PROPRIETARY AI OPPORTUNITIES
Where should the company build custom AI using its own data?

Return ONLY valid JSON:
{{
  "ai_automation": [
    {{
      "name": "Implement [Tool] for [Function]",
      "category": "AI Automation",
      "description": "[Tool] costs $X/month. Automates [task]. Saves Y hrs/month at $Z/hr = $W/month. Net annual: $V.",
      "ebitda_impact_annual": 12345,
      "implementation_cost": 5000,
      "timeline_months": 3,
      "confidence": "High|Medium|Low",
      "specific_tools": ["ToolName"],
      "research_source": "AI research: [source]"
    }}
  ],
  "ai_product_recommendations": ["Specific recommendation with sizing"],
  "ai_disruption_risks": ["Specific risk with impact estimate"],
  "proprietary_ai_opportunities": ["Specific opportunity with investment estimate"]
}}"""

    try:
        client = Anthropic()
        # Clean context of problematic chars
        clean_context = re.sub(r'[{}]', '', context_block)
        clean_research = re.sub(r'[{}]', '', research_results[:6000])
        clean_message = f"COMPANY DATA:\n{clean_context}\n\nAI RESEARCH RESULTS:\n{clean_research}"

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": clean_message}],
        )

        text = response.content[0].text.strip()
        # Extract JSON robustly
        from value_creation.financial_agent import _clean_json_text
        text = _clean_json_text(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}

        # Parse automation opportunities into SizedInitiatives
        automations = []
        for item in data.get("ai_automation", []):
            automations.append(SizedInitiative(
                name=item.get("name", ""),
                category="AI Automation",
                description=item.get("description", ""),
                ebitda_impact_annual=float(item.get("ebitda_impact_annual", 0)),
                implementation_cost=float(item.get("implementation_cost", 0)),
                timeline_months=int(item.get("timeline_months", 3)),
                confidence=item.get("confidence", "Medium"),
                specific_tools=item.get("specific_tools", []),
                research_source=item.get("research_source", ""),
            ))

        return {
            "ai_automation": automations,
            "ai_product_recommendations": data.get("ai_product_recommendations", []),
            "ai_disruption_risks": data.get("ai_disruption_risks", []),
            "proprietary_ai_opportunities": data.get("proprietary_ai_opportunities", []),
        }

    except Exception:
        return {}
