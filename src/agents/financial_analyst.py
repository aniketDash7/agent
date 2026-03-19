"""
CapitalMind — Financial Analyst Agent.
Extracts financial metrics, computes ratios, analyzes EPS performance.
"""
from __future__ import annotations
from typing import Any


class FinancialAnalystAgent:
    """Agent that analyzes financial statements and computes key metrics."""

    def __init__(self, llm):
        self.llm = llm

    async def analyze(
        self,
        ticker: str,
        context_chunks: list[dict],
        extracted_tables: list[dict],
        market_snapshot: dict | None = None,
    ) -> dict[str, Any]:
        """
        Analyze financial data and return FinancialMetrics dict.

        Uses LLM to extract and compute:
        - Revenue, margins (gross, operating, net)
        - EPS actual vs consensus
        - FCF, D/E ratio, current ratio, ROE
        - Valuation multiples (P/E, EV/EBITDA)
        """
        # Build analysis prompt from context chunks and tables
        context_text = "\n".join(
            chunk.get("text", "") for chunk in context_chunks[:10]
        )

        prompt = f"""Analyze the financial data for {ticker}.
Extract key financial metrics from the following context:

{context_text[:4000]}

Return a JSON object with: revenue, gross_margin, operating_margin,
net_margin, eps, eps_beat, revenue_growth_yoy, fcf, debt_to_equity,
current_ratio, roe, pe_ratio, ev_ebitda."""

        response = await self.llm.ainvoke(prompt)
        # Parse LLM response into structured metrics
        # In production, this would parse JSON from the response
        return {
            "ticker": ticker,
            "period": "Latest",
            "revenue": None,
            "gross_margin": None,
            "operating_margin": None,
            "net_margin": None,
            "eps": None,
            "eps_beat": None,
            "revenue_growth_yoy": None,
            "fcf": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "roe": None,
            "pe_ratio": None,
            "ev_ebitda": None,
            "raw": {},
        }
