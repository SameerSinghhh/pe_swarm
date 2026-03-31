"""
Company profile builder. Uses Claude to UNDERSTAND the company before
doing any research. This is the intelligence layer that makes research
targeted instead of generic.

One API call. Claude analyzes the company name + sector + financials
and returns: what the company does, who the real comps are, and what
specific questions to research.
"""

import json
import os
from dotenv import load_dotenv

from research.types import CompanyProfile

load_dotenv()


def build_company_profile(
    company_name: str,
    sector: str,
    company_metrics: dict,
    business_description: str = "",
) -> CompanyProfile:
    """
    Use Claude to build an understanding of the company.

    Input: company name, sector, key financial metrics, optional description.
    Output: CompanyProfile with suggested comps, research queries, competitive factors.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return _fallback_profile(company_name, sector)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return _fallback_profile(company_name, sector)

    # Build metrics text
    metrics_text = ""
    if company_metrics:
        lines = []
        for k, v in company_metrics.items():
            if v is not None:
                if "pct" in k or "margin" in k or "growth" in k:
                    lines.append(f"- {k}: {v:.1f}%")
                elif isinstance(v, float) and v > 10000:
                    lines.append(f"- {k}: ${v:,.0f}")
                else:
                    lines.append(f"- {k}: {v}")
        metrics_text = "\n".join(lines)

    desc_text = f"\nBusiness description provided: {business_description}" if business_description else ""

    prompt = f"""You are a PE analyst building a company profile to guide competitive research.

COMPANY: {company_name}
SECTOR: {sector}{desc_text}

FINANCIAL METRICS:
{metrics_text or "Not provided"}

Based on this information, determine:

1. What this company likely does (its product/service, target market, business model)
2. The specific sub-sector (not just "SaaS" but "workflow automation SaaS" or "healthcare billing SaaS" etc.)
3. Revenue scale bracket based on the metrics
4. 5 REAL publicly traded comparable companies that are:
   - In the same or very similar sub-sector
   - Reasonably comparable in business model (not just any tech company)
   - Include a mix of sizes (some similar scale, some larger aspirational comps)
   - Must be real tickers that trade on US exchanges
5. 5 specific research queries that would uncover the most relevant competitive and market intelligence for THIS specific company
6. Key competitive factors in this market

Return ONLY this JSON (no markdown, no code fences):
{{
  "business_description": "One sentence describing what this company does",
  "sub_sector": "Specific sub-sector name",
  "revenue_bracket": "$X-YM",
  "target_market": "Who they sell to",
  "business_model": "How they make money",
  "suggested_comps": [
    {{"ticker": "XXXX", "name": "Company Name", "reason": "Why this is a good comp"}},
    {{"ticker": "YYYY", "name": "Company Name", "reason": "Why this is a good comp"}},
    {{"ticker": "ZZZZ", "name": "Company Name", "reason": "Why this is a good comp"}},
    {{"ticker": "WWWW", "name": "Company Name", "reason": "Why this is a good comp"}},
    {{"ticker": "VVVV", "name": "Company Name", "reason": "Why this is a good comp"}}
  ],
  "research_queries": [
    "Specific research query 1 about this company's market",
    "Specific research query 2 about competitors",
    "Specific research query 3 about market trends",
    "Specific research query 4 about pricing/benchmarks",
    "Specific research query 5 about risks or disruption"
  ],
  "key_competitive_factors": ["factor1", "factor2", "factor3", "factor4"]
}}"""

    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Strip code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3].strip()

        data = json.loads(text)

        return CompanyProfile(
            business_description=data.get("business_description", ""),
            sub_sector=data.get("sub_sector", sector),
            revenue_bracket=data.get("revenue_bracket", ""),
            target_market=data.get("target_market", ""),
            business_model=data.get("business_model", ""),
            suggested_comps=data.get("suggested_comps", []),
            research_queries=data.get("research_queries", []),
            key_competitive_factors=data.get("key_competitive_factors", []),
        )

    except Exception:
        return _fallback_profile(company_name, sector)


def _fallback_profile(company_name: str, sector: str) -> CompanyProfile:
    """Fallback when Claude is unavailable. Uses generic defaults."""
    from research.peers import suggest_peers

    tickers = suggest_peers(sector)

    return CompanyProfile(
        business_description=f"{company_name} operating in {sector}",
        sub_sector=sector,
        research_queries=[
            f"{sector} industry trends outlook 2025 2026",
            f"{sector} competitive landscape market size",
            f"{sector} benchmarks margins growth rates",
        ],
        suggested_comps=[{"ticker": t, "name": t, "reason": "Sector match"} for t in tickers],
    )
