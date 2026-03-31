"""
Agent 3: Strategic Positioning.

Focuses on exit value maximization, risk assessment, and strategic priorities.
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()


def run_strategic_agent(context_block: str, company_name: str) -> dict:
    """Run the strategic positioning agent."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return {}

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return {}

    system_prompt = f"""You are a PE investment professional focused on exit value maximization for {company_name}.

Analyze the financial data and market context to determine:

1. STRATEGIC PRIORITIES (3-5)
Highest-impact moves to maximize exit value. Consider: bolt-on M&A, market expansion, business model shifts, growth vs profitability balance.

2. KEY RISKS (3-5)
What could destroy 20%+ of enterprise value? Be specific: name the threat, probability, dollar impact, and mitigation.

3. EXIT READINESS
What would make a buyer pay a premium? What gaps need closing? Consider: recurring revenue quality, customer diversification, management team, technology moat, growth trajectory.

Return ONLY valid JSON:
{{
  "strategic_priorities": [
    "Priority: [Specific action]. [Why it increases exit value]. [Estimated impact on multiple]."
  ],
  "key_risks": [
    "Risk: [Threat]. Probability: [H/M/L]. Impact: [$X or Y% of EV]. Mitigation: [specific action]."
  ],
  "exit_readiness_notes": "2-3 paragraph assessment."
}}"""

    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": context_block}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"): text = text[:-3].strip()

        return json.loads(text)

    except Exception:
        return {}
