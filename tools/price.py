"""Price lookup tool backed by yfinance, with a short in-memory cache
so repeated questions about the same ticker don't hit yfinance every time."""

import time
import yfinance as yf

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 60

TICKER_ALIASES = {
    "VFV": "VFV.TO",
    "XIU": "XIU.TO",
    "XIC": "XIC.TO",
    "ZCN": "ZCN.TO",
    "VCN": "VCN.TO",
    "XGRO": "XGRO.TO",
    "VGRO": "VGRO.TO",
    "VEQT": "VEQT.TO",
    "XEQT": "XEQT.TO",
    "ZSP": "ZSP.TO",
    "SHOP": "SHOP.TO",
    "VWRA": "VWRA.L",
    "VWRL": "VWRL.L",
    "7203": "7203.T",
    "9988": "9988.HK",
}


def normalize_ticker(ticker: str) -> tuple[str, str]:
    """Return the user-facing ticker and its Yahoo Finance symbol."""
    requested_ticker = ticker.upper().strip()
    yahoo_ticker = TICKER_ALIASES.get(requested_ticker, requested_ticker)
    return requested_ticker, yahoo_ticker


def get_price(ticker: str) -> dict:
    """Return the latest price and daily change for a stock or ETF ticker."""
    requested_ticker, ticker = normalize_ticker(ticker)
    now = time.time()

    cached = _cache.get(ticker)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info  # lighter/faster than the full .info dict

        price = info["last_price"]
        prev_close = info["previous_close"]
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else None

        data = {
            "ticker": requested_ticker,
            "yahoo_ticker": ticker,
            "price": round(price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2) if change_pct is not None else None,
            "currency": getattr(info, "currency", "USD"),
        }
    except Exception as e:
        return {
            "ticker": requested_ticker,
            "yahoo_ticker": ticker,
            "error": f"Could not fetch price for {ticker}: {e}",
        }

    _cache[ticker] = (now, data)
    return data