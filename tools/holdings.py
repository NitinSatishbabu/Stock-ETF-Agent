"""ETF holdings lookup backed by yfinance."""

import math
from typing import Any

import yfinance as yf

from tools.price import normalize_ticker


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def get_holdings(ticker: str, limit: int = 10) -> dict:
    """Return the largest reported holdings for an ETF."""
    requested_ticker, yahoo_ticker = normalize_ticker(ticker)
    limit = max(1, min(limit, 25))

    try:
        fund = yf.Ticker(yahoo_ticker)
        holdings = fund.get_holdings()
        if holdings is None or holdings.empty:
            return {
                "ticker": requested_ticker,
                "yahoo_ticker": yahoo_ticker,
                "holdings": [],
                "error": f"No holdings data found for {yahoo_ticker}",
            }

        rows = []
        for symbol, row in holdings.head(limit).iterrows():
            holding = {
                "symbol": str(symbol),
                "name": _clean_value(row.get("Name")),
                "holding_percent": _clean_value(row.get("Holding Percent")),
                "market_value": _clean_value(row.get("Market Value")),
            }
            rows.append({key: value for key, value in holding.items() if value is not None})

        return {
            "ticker": requested_ticker,
            "yahoo_ticker": yahoo_ticker,
            "holdings": rows,
            "returned_count": len(rows),
        }
    except Exception as error:
        return {
            "ticker": requested_ticker,
            "yahoo_ticker": yahoo_ticker,
            "holdings": [],
            "error": f"Could not fetch holdings for {yahoo_ticker}: {error}",
        }
