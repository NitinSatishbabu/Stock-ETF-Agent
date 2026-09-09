"""ETF profile lookup backed by yfinance."""

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


def get_etf_profile(ticker: str) -> dict:
    """Return descriptive profile and fee information for an ETF."""
    requested_ticker, yahoo_ticker = normalize_ticker(ticker)

    try:
        info = yf.Ticker(yahoo_ticker).info
        if not info:
            return {
                "ticker": requested_ticker,
                "yahoo_ticker": yahoo_ticker,
                "error": f"No profile data found for {yahoo_ticker}",
            }

        profile = {
            "ticker": requested_ticker,
            "yahoo_ticker": yahoo_ticker,
            "name": _clean_value(info.get("longName") or info.get("shortName")),
            "quote_type": _clean_value(info.get("quoteType")),
            "category": _clean_value(info.get("category")),
            "fund_family": _clean_value(info.get("fundFamily")),
            "description": _clean_value(info.get("longBusinessSummary")),
            "currency": _clean_value(info.get("currency")),
            "exchange": _clean_value(info.get("exchange")),
            "inception_date": _clean_value(info.get("fundInceptionDate")),
            "expense_ratio": _clean_value(info.get("annualReportExpenseRatio")),
            "total_assets": _clean_value(info.get("totalAssets")),
            "yield": _clean_value(info.get("yield")),
            "annual_return": _clean_value(info.get("annualReturn")),
            "ytd_return": _clean_value(info.get("ytdReturn")),
        }
        return {key: value for key, value in profile.items() if value is not None}
    except Exception as error:
        return {
            "ticker": requested_ticker,
            "yahoo_ticker": yahoo_ticker,
            "error": f"Could not fetch ETF profile for {yahoo_ticker}: {error}",
        }
