"""
Load historical quarterly financials from yfinance and map to our schema.

Handles the messy reality of yfinance data: varying field names, missing
fields, NaN handling, and timestamp-to-period conversion.
"""

import os
import json
import math
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def load_company_history(ticker: str, use_cache: bool = True) -> dict[str, pd.DataFrame] | None:
    """
    Load historical quarterly financials for a company.
    Returns dict with "income_statement" and "balance_sheet" DataFrames
    in our standard schema, or None if data is insufficient.
    """
    # Check cache
    cache_file = CACHE_DIR / f"{ticker}.json"
    if use_cache and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            is_df = pd.DataFrame(cached["income_statement"])
            bs_df = pd.DataFrame(cached["balance_sheet"]) if cached.get("balance_sheet") else None
            if len(is_df) >= 8:
                return {"income_statement": is_df, "balance_sheet": bs_df}
        except Exception:
            pass

    # Fetch from yfinance
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
    except Exception:
        return None

    # Income statement
    is_df = _build_income_statement(t)
    if is_df is None or len(is_df) < 4:
        return None

    # Balance sheet
    bs_df = _build_balance_sheet(t)

    # Cache
    try:
        cache_data = {
            "income_statement": is_df.to_dict(orient="records"),
            "balance_sheet": bs_df.to_dict(orient="records") if bs_df is not None else None,
        }
        cache_file.write_text(json.dumps(cache_data, default=str))
    except Exception:
        pass

    return {"income_statement": is_df, "balance_sheet": bs_df}


def _build_income_statement(t) -> pd.DataFrame | None:
    """Extract and map quarterly income statement to our schema."""
    try:
        q = t.quarterly_financials
        if q is None or q.empty:
            return None
    except Exception:
        return None

    rows = []
    for col in q.columns:
        period = col.strftime("%Y-%m")
        data = q[col]

        revenue = _get(data, ["Total Revenue", "Operating Revenue"])
        cogs = _get(data, ["Cost Of Revenue", "Reconciled Cost Of Revenue"])
        gross_profit = _get(data, ["Gross Profit"])
        sm = _get(data, ["Selling And Marketing Expense", "Selling General And Administration"])
        rd = _get(data, ["Research And Development"])
        ga = _get(data, ["General And Administrative Expense", "Other Gand A"])
        total_opex = _get(data, ["Operating Expense"])
        ebitda = _get(data, ["EBITDA", "Normalized EBITDA"])

        if revenue is None or revenue <= 0:
            continue

        # Derive missing fields
        if gross_profit is None and cogs is not None:
            gross_profit = revenue - cogs
        if cogs is None and gross_profit is not None:
            cogs = revenue - gross_profit
        if ebitda is None and gross_profit is not None and total_opex is not None:
            ebitda = gross_profit - total_opex
        if total_opex is None:
            opex_sum = (sm or 0) + (rd or 0) + (ga or 0)
            if opex_sum > 0:
                total_opex = opex_sum

        # If we got SGA but not separate S&M and G&A, split it
        if sm is not None and ga is None and sm > 0:
            # Check if we got the combined SGA number
            sga_val = _get(data, ["Selling General And Administration"])
            sm_val = _get(data, ["Selling And Marketing Expense"])
            ga_val = _get(data, ["General And Administrative Expense"])
            if sga_val and not sm_val:
                # We only have combined SGA — split 75/25
                sm = sga_val * 0.75
                ga = sga_val * 0.25
            elif sm_val and ga_val:
                sm = sm_val
                ga = ga_val

        rows.append({
            "period": period,
            "revenue": revenue,
            "cogs": cogs or 0,
            "gross_profit": gross_profit or 0,
            "sales_marketing": sm or 0,
            "rd": rd or 0,
            "ga": ga or 0,
            "total_opex": total_opex or 0,
            "ebitda": ebitda or 0,
        })

    if len(rows) < 3:
        return None

    df = pd.DataFrame(rows)
    df = df.sort_values("period").reset_index(drop=True)
    return df


def _build_balance_sheet(t) -> pd.DataFrame | None:
    """Extract and map quarterly balance sheet to our schema."""
    try:
        bs = t.quarterly_balance_sheet
        if bs is None or bs.empty:
            return None
    except Exception:
        return None

    rows = []
    for col in bs.columns:
        period = col.strftime("%Y-%m")
        data = bs[col]

        ar = _get(data, ["Accounts Receivable", "Net Receivable", "Receivables"])
        ap = _get(data, ["Accounts Payable"])
        inventory = _get(data, ["Inventory"])
        cash = _get(data, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        total_debt = _get(data, ["Total Debt"])
        total_assets = _get(data, ["Total Assets"])

        rows.append({
            "period": period,
            "accounts_receivable": ar or 0,
            "accounts_payable": ap or 0,
            "inventory": inventory or 0,
            "cash": cash or 0,
            "long_term_debt": total_debt or 0,
            "short_term_debt": 0,
            "total_assets": total_assets or 0,
        })

    if len(rows) < 3:
        return None

    df = pd.DataFrame(rows)
    df = df.sort_values("period").reset_index(drop=True)
    return df


def _get(series: pd.Series, field_names: list[str]) -> float | None:
    """Try multiple field names, return first non-null value."""
    for name in field_names:
        try:
            val = series.get(name)
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                return float(val)
        except Exception:
            continue
    return None


def get_company_sector(ticker: str) -> str:
    """Get the sector/industry for a ticker."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        return _map_sector(sector, industry)
    except Exception:
        return "Other"


def _map_sector(sector: str, industry: str) -> str:
    """Map yfinance sector/industry to our benchmark sectors."""
    industry_lower = industry.lower()
    sector_lower = sector.lower()

    if "software" in industry_lower or "saas" in industry_lower:
        return "B2B SaaS"
    if "internet" in industry_lower or "information technology" in industry_lower:
        return "Software"
    if "health" in sector_lower or "health" in industry_lower:
        return "Healthcare Services"
    if "manufacturing" in industry_lower or "industrial" in sector_lower:
        return "Manufacturing"
    if "retail" in industry_lower or "consumer" in sector_lower:
        return "Retail"
    if "distribution" in industry_lower or "logistics" in industry_lower:
        return "Distribution"
    if "services" in industry_lower:
        return "Services"

    return "Other"
