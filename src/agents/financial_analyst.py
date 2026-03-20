"""
CapitalMind — Financial Analyst Agent.
Extracts financial metrics, computes ratios, analyzes EPS performance.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage


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
        """
        # Combine context chunks and tables for analysis
        # In a real app, we'd pass structured table data too
        context_text = "\n\n".join([
             f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}"
             for c in context_chunks[:15]
        ])

        system_prompt = """You are an institutional Financial Analyst. 
Your task is to extract exact financial metrics from the provided filing text and tables.
Return ONLY valid JSON. If a value is unknown, return null. 
Ensure numbers are in absolute values (e.g., 25.5B for billions)."""

        user_prompt = f"""Ticker: {ticker}
Market Snapshot: {json.dumps(market_snapshot, indent=2) if market_snapshot else 'N/A'}

Context Data:
{context_text[:12000]}

Extract the following metrics for the most recent fiscal period:
1. revenue (sum of revenue)
2. gross_margin (%)
3. operating_margin (%)
4. net_margin (%)
5. eps (diluted earnings per share)
6. eps_beat (vs consensus if mentioned, else null)
7. revenue_growth_yoy (%)
8. fcf (free cash flow)
9. debt_to_equity
10. current_ratio
11. roe (%)
12. pe_ratio
13. ev_ebitda

Return JSON format:
{{
  "ticker": string,
  "period": string,
  "revenue": string,
  "gross_margin": float,
  "operating_margin": float,
  "net_margin": float,
  "eps": float,
  "eps_beat": float,
  "revenue_growth_yoy": float,
  "fcf": string,
  "debt_to_equity": float,
  "current_ratio": float,
  "roe": float,
  "pe_ratio": float,
  "ev_ebitda": float,
  "summary": string (2-sentence summary of financial health)
}}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            
            # Extract JSON from response (handling potential markdown fences)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            data["raw"] = {} # Placeholder for raw extracted data
            return data
            
        except Exception as e:
            return {
                "ticker": ticker,
                "period": "Error during analysis",
                "error": str(e),
                "revenue": None,
                "summary": "Failed to extract data correctly."
            }
