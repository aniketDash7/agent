"""
CapitalMind — Market Data Client.
Real-time and historical market data via yfinance.
"""
from __future__ import annotations
from typing import Any
import yfinance as ticker_mod
import asyncio


class MarketDataClient:
    """Client for fetching real-time market data via yfinance."""

    async def get_snapshot(self, ticker: str) -> dict[str, Any]:
        """
        Get current market snapshot for a ticker using yfinance.
        """
        try:
            # Run yfinance in thread to avoid blocking async loop
            t = ticker_mod.Ticker(ticker)
            info = await asyncio.to_thread(lambda: t.info)
            
            return {
                "ticker": ticker,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "currency": info.get("currency", "USD"),
                "change_pct": info.get("regularMarketChangePercent"),
                "volume": info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "timestamp": None,  # Can add actual timestamp if needed
            }
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "price": None,
            }

    async def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> Any:
        """Fetch historical price data for charts."""
        t = ticker_mod.Ticker(ticker)
        history = await asyncio.to_thread(lambda: t.history(period=period, interval=interval))
        return history
