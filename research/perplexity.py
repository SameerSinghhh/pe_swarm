"""
Perplexity API wrapper for targeted research and news.

Uses the profile's custom queries instead of generic searches.
"""

import os
import requests
from dotenv import load_dotenv

from research.types import NewsItem

load_dotenv()


def search(query: str, max_results: int = 5) -> list[dict]:
    """Raw web search via Perplexity /search endpoint."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return []

    try:
        r = requests.post(
            "https://api.perplexity.ai/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "max_results": max_results,
                "max_tokens_per_page": 300,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []


def ai_search(query: str) -> str:
    """AI-synthesized search via Perplexity /v1/responses endpoint."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return ""

    try:
        r = requests.post(
            "https://api.perplexity.ai/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"preset": "fast-search", "input": query},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        for item in data.get("output", []):
            if item.get("type") == "message" and item.get("role") == "assistant":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        return c.get("text", "")
        return ""
    except Exception:
        return ""


def research_with_queries(queries: list[str]) -> str:
    """
    Run targeted research using the profile's custom queries.
    Returns combined AI-synthesized context from all queries.
    """
    sections = []

    for query in queries[:4]:  # Limit to 4 queries to control cost/latency
        result = ai_search(query)
        if result:
            sections.append(result)

    return "\n\n---\n\n".join(sections)


def get_targeted_news(
    company_name: str,
    competitor_names: list[str],
    sub_sector: str,
    max_items: int = 8,
) -> list[NewsItem]:
    """
    Search for news about the company, its specific competitors,
    and its specific sub-sector. Targeted, not generic.
    """
    news = []

    # Company-specific
    for result in search(f'"{company_name}" news announcements', max_results=3):
        news.append(_result_to_news(result, "company"))

    # Competitor news
    if competitor_names:
        comp_query = " OR ".join(f'"{name}"' for name in competitor_names[:3])
        for result in search(f"{comp_query} news", max_results=3):
            news.append(_result_to_news(result, "competitor"))

    # Sub-sector specific
    for result in search(f"{sub_sector} market news deals acquisitions 2025 2026", max_results=3):
        news.append(_result_to_news(result, "industry"))

    return news[:max_items]


def _result_to_news(result: dict, relevance: str) -> NewsItem:
    return NewsItem(
        title=result.get("title", ""),
        source=result.get("url", ""),
        date=result.get("date", result.get("last_updated", "")),
        snippet=result.get("snippet", ""),
        relevance=relevance,
        url=result.get("url", ""),
    )
