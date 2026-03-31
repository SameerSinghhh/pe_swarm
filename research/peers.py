"""
Peer company financials via yfinance.

Pulls key metrics for public comparable companies: revenue, margins,
growth, multiples. Fast, free, and reliable for the metrics PE firms care about.
"""

from research.types import PeerCompany


def get_peer_financials(tickers: list[str]) -> list[PeerCompany]:
    """
    Pull financial metrics for a list of public company tickers.
    Returns PeerCompany for each ticker that has data.
    Gracefully skips tickers that fail.
    """
    try:
        import yfinance as yf
    except ImportError:
        return []

    peers = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info

            if not info or not info.get("longName"):
                continue

            revenue = info.get("totalRevenue")
            gm = info.get("grossMargins")
            em = info.get("ebitdaMargins")
            rg = info.get("revenueGrowth")
            mcap = info.get("marketCap")
            ev_ebitda = info.get("enterpriseToEbitda")

            peers.append(PeerCompany(
                name=info.get("longName", ticker),
                ticker=ticker,
                revenue=float(revenue) if revenue else None,
                gross_margin_pct=round(gm * 100, 1) if gm else None,
                ebitda_margin_pct=round(em * 100, 1) if em else None,
                revenue_growth_yoy_pct=round(rg * 100, 1) if rg else None,
                market_cap=float(mcap) if mcap else None,
                ev_to_ebitda=round(float(ev_ebitda), 1) if ev_ebitda else None,
                source="yfinance",
            ))

        except Exception:
            continue

    return peers


# Common peer groups by sector
PEER_GROUPS = {
    "B2B SaaS": ["CRM", "HUBS", "ZS", "DDOG", "NET", "BILL", "ZI"],
    "Software": ["CRM", "NOW", "ADBE", "INTU", "WDAY", "TEAM"],
    "Manufacturing": ["HON", "EMR", "ROK", "ETN", "DOV", "ITW"],
    "Services": ["ACN", "IT", "LDOS", "BAH", "CACI", "SAIC"],
    "Healthcare Services": ["UHS", "THC", "HCA", "EHC", "AMED"],
    "Distribution": ["FAST", "GWW", "MSM", "WCC", "POOL"],
    "Retail": ["AMZN", "TGT", "COST", "WMT", "HD", "LOW"],
}


def suggest_peers(sector: str) -> list[str]:
    """Suggest peer tickers for a given sector."""
    sector_lower = sector.lower().strip()
    for key, tickers in PEER_GROUPS.items():
        if key.lower() in sector_lower or sector_lower in key.lower():
            return tickers[:5]  # Return top 5
    # Default: broad SaaS/tech
    return ["CRM", "HUBS", "DDOG", "NET", "ZS"]
