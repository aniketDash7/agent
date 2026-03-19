"""
CapitalMind — SEC EDGAR Async Client.
Fetches 10-K, 10-Q, 8-K filings and earnings transcripts from the SEC EDGAR API.
"""
from __future__ import annotations
from typing import Any


class SECEdgarClient:
    """Async client for SEC EDGAR REST API."""

    EDGAR_BASE = "https://efts.sec.gov/LATEST"

    async def fetch_latest(
        self,
        filing_type: str,
        ticker: str,
        count: int = 1,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        Fetch the latest filing(s) of the given type for a ticker.
        Returns raw document references with S3 URIs and metadata.
        """
        # In production: call EDGAR API, download filing, upload to S3
        return {
            "document_type": filing_type,
            "ticker": ticker,
            "filing_date": None,
            "source": f"sec-edgar/{ticker}/{filing_type}",
            "content": "",
        }

    async def fetch_earnings_transcript(
        self,
        ticker: str,
    ) -> dict[str, Any] | None:
        """Fetch the latest earnings call transcript."""
        return {
            "document_type": "earnings_transcript",
            "ticker": ticker,
            "filing_date": None,
            "source": f"transcript/{ticker}",
            "content": "",
        }
