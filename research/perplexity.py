"""
Perplexity API wrapper for industry research and news.

Uses the /search endpoint for raw results (reliable, structured)
and /v1/responses for AI-synthesized industry context.
"""

import os
import requests
from dotenv import load_dotenv

from research.types import NewsItem

load_dotenv()


def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Raw web search via Perplexity /search endpoint.
    Returns list of result dicts with: title, url, snippet, date.
    """
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
        data = r.json()
        return data.get("results", [])
    except Exception:
        return []


def research_industry(company_name: str, sector: str) -> str:
    """
    Use Perplexity AI search to get industry context.
    Returns a synthesized paragraph about the industry.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return ""

    query = f"{sector} industry trends outlook 2025 2026 growth rates competitive landscape"

    try:
        r = requests.post(
            "https://api.perplexity.ai/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "preset": "fast-search",
                "input": query,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        # Extract the text output
        output = data.get("output", [])
        for item in output:
            if item.get("type") == "message" and item.get("role") == "assistant":
                content = item.get("content", [])
                for c in content:
                    if c.get("type") == "output_text":
                        return c.get("text", "")
        return ""
    except Exception:
        return ""


def get_recent_news(company_name: str, sector: str, max_items: int = 5) -> list[NewsItem]:
    """
    Search for recent news about the company and its sector.
    """
    news = []

    # Company-specific news
    company_results = search(f"{company_name} latest news", max_results=3)
    for r in company_results:
        news.append(NewsItem(
            title=r.get("title", ""),
            source=r.get("url", ""),
            date=r.get("date", r.get("last_updated", "")),
            snippet=r.get("snippet", ""),
            relevance="company",
            url=r.get("url", ""),
        ))

    # Industry news
    industry_results = search(f"{sector} industry news deals acquisitions", max_results=3)
    for r in industry_results:
        news.append(NewsItem(
            title=r.get("title", ""),
            source=r.get("url", ""),
            date=r.get("date", r.get("last_updated", "")),
            snippet=r.get("snippet", ""),
            relevance="industry",
            url=r.get("url", ""),
        ))

    return news[:max_items]
