"""
Macro context via yfinance.

Pulls current market data: S&P 500, treasury yields, sector ETF performance.
"""

from datetime import date, timedelta
from research.types import MacroContext


def get_macro_context(sector: str = "") -> MacroContext:
    """
    Pull current macro/market data.
    Uses yfinance for market indices and yields.
    """
    try:
        import yfinance as yf
    except ImportError:
        return MacroContext(as_of_date=date.today().isoformat())

    ctx = MacroContext(as_of_date=date.today().isoformat())

    try:
        # S&P 500
        sp = yf.Ticker("^GSPC")
        hist = sp.history(period="1y")
        if not hist.empty:
            ctx.sp500_level = round(float(hist["Close"].iloc[-1]), 0)
            start_price = float(hist["Close"].iloc[0])
            ctx.sp500_ytd_pct = round((ctx.sp500_level - start_price) / start_price * 100, 1)
    except Exception:
        pass

    try:
        # 10-year Treasury yield
        tny = yf.Ticker("^TNX")
        hist = tny.history(period="5d")
        if not hist.empty:
            ctx.treasury_10y = round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass

    try:
        # Fed Funds Rate proxy (2-year treasury as approximation)
        ff = yf.Ticker("^IRX")  # 13-week T-bill
        hist = ff.history(period="5d")
        if not hist.empty:
            ctx.fed_funds_rate = round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass

    try:
        # Sector ETF performance
        etf = _sector_etf(sector)
        if etf:
            t = yf.Ticker(etf)
            hist = t.history(period="1y")
            if not hist.empty:
                start = float(hist["Close"].iloc[0])
                end = float(hist["Close"].iloc[-1])
                ctx.sector_etf_ytd_pct = round((end - start) / start * 100, 1)
    except Exception:
        pass

    return ctx


SECTOR_ETFS = {
    "b2b saas": "IGV",      # iShares Software ETF
    "software": "IGV",
    "technology": "XLK",     # Technology Select SPDR
    "manufacturing": "XLI",  # Industrials Select SPDR
    "services": "XLK",
    "healthcare": "XLV",     # Health Care Select SPDR
    "healthcare services": "XLV",
    "distribution": "XLI",
    "retail": "XRT",         # SPDR S&P Retail ETF
    "logistics": "IYT",      # iShares Transportation Avg ETF
}


def _sector_etf(sector: str) -> str | None:
    """Find the relevant sector ETF ticker."""
    return SECTOR_ETFS.get(sector.lower().strip())
