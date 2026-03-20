"""
CapitalMind — SEC EDGAR Async Client.
Fetches 10-K, 10-Q, 8-K filings from the SEC EDGAR API.
"""
from __future__ import annotations
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

class SECEdgarClient:
    """Async client for SEC EDGAR REST API."""

    SEC_DIRECTORY_URL = "https://www.sec.gov/files/company_tickers.json"
    USER_AGENT = "CapitalMind/1.0 (analyst@firm.com)"

    async def _get_cik(self, ticker: str) -> str | None:
        """Resolve ticker to CIK (Central Index Key) via SEC tickers mapping."""
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": self.USER_AGENT}
            response = await client.get(self.SEC_DIRECTORY_URL, headers=headers)
            if response.status_code != 200:
                return None
            
            data = response.json()
            ticker = ticker.upper()
            for item in data.values():
                if item["ticker"] == ticker:
                    # Pad CIK to 10 digits
                    return str(item["cik_str"]).zfill(10)
        return None

    async def fetch_latest(
        self,
        filing_type: str,
        ticker: str,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Fetch references to the latest filing(s) of the given type for a ticker.
        """
        cik = await self._get_cik(ticker)
        if not cik:
            logger.error(f"Could not find CIK for ticker {ticker}")
            return []

        # SEC Submissions API for the CIK
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": self.USER_AGENT}
            response = await client.get(submissions_url, headers=headers)
            if response.status_code != 200:
                return []
            
            data = response.json()
            filings = data.get("filings", {}).get("recent", {})
            
            results = []
            for i, f_type in enumerate(filings.get("form", [])):
                if f_type == filing_type:
                    acc_num = filings.get("accessionNumber", [])[i].replace("-", "")
                    doc_name = filings.get("primaryDocument", [])[i]
                    date = filings.get("filingDate", [])[i]
                    
                    # Direct URL to the filing HTML/Text on SEC.gov
                    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{doc_name}"
                    
                    results.append({
                        "document_type": filing_type,
                        "ticker": ticker,
                        "filing_date": date,
                        "url": url,
                        "source": f"sec-edgar/{ticker}/{filing_type}/{acc_num}",
                        "content": "", # Would be populated by a separate fetch if needed
                    })
                    if len(results) >= count:
                        break
            
            return results

    async def fetch_earnings_transcript(
        self,
        ticker: str,
    ) -> dict[str, Any] | None:
        """
        Mock for earnings transcripts.
        (Real transcripts often require paid APIs like Seeking Alpha or Alpha Vantage).
        """
        # For demo purposes, we'll return a placeholder that the graph can use.
        return {
            "document_type": "earnings_transcript",
            "ticker": ticker,
            "filing_date": "2024-Q3",
            "source": f"transcript/{ticker}",
            "content": f"Earnings call transcript for {ticker} Q3 2024. Management discusses revenue growth and AI investments.",
        }
