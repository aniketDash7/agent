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
        context_text = "\n\n".join([
             f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}"
             for c in context_chunks[:30]
        ])

        system_prompt = """You are an institutional Financial Analyst. 
Return ONLY valid JSON. If a value is unknown, return null. 
CRITICAL: Return Revenue and FCF in BILLIONS (e.g. 88.27). 
Convert millions to billions automatically (88,268M -> 88.268)."""

        user_prompt = f"""Ticker: {ticker}
Market Snapshot: {json.dumps(market_snapshot, indent=2) if market_snapshot else 'N/A'}

Extract the following for the MOST RECENT period:
1. revenue (Billions USD)
2. gross_margin (decimal, e.g. 0.42)
3. operating_margin (decimal)
4. net_margin (decimal)
5. eps (dollars)
6. eps_beat (decimal, e.g. 0.03 for 3% beat)
7. revenue_growth_yoy (decimal, e.g. 0.12)
8. fcf (Billions USD)
9. debt_to_equity (float)
10. current_ratio (float)
11. roe (decimal)
12. pe_ratio (float)
13. ev_ebitda (float)

Context Data:
{context_text[:15000]}

Return JSON:
{{
  "ticker": "{ticker}",
  "period": "string",
  "revenue": float,
  "gross_margin": float,
  "operating_margin": float,
  "net_margin": float,
  "eps": float,
  "eps_beat": float,
  "revenue_growth_yoy": float,
  "fcf": float,
  "debt_to_equity": float,
  "current_ratio": float,
  "roe": float,
  "pe_ratio": float,
  "ev_ebitda": float,
  "summary": "2-sentence summary"
}}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # --- NORMALIZATION LAYER ---
            for key in ["revenue", "fcf"]:
                val = data.get(key)
                if isinstance(val, (int, float)):
                    if val > 10_000_000: # Clearly absolute dollars (e.g. 307,000,000,000)
                        data[key] = round(val / 1_000_000_000, 3)
                    elif val > 1000: # Likely millions (e.g. 88,268)
                        data[key] = round(val / 1000, 3)
                    # Small values (e.g. 88.27) are assumed to be already in Billions

            # Sanity check percentages (if they returned 25 instead of 0.25)
            for key in ["gross_margin", "operating_margin", "revenue_growth_yoy", "eps_beat"]:
                val = data.get(key)
                if isinstance(val, (int, float)) and abs(val) > 1.0:
                    data[key] = round(val / 100, 4)

            data["raw"] = {} 
            return data
            
        except Exception as e:
            return {
                "ticker": ticker,
                "period": "Error during analysis",
                "error": str(e),
                "revenue": None,
                "summary": "Failed to extract data correctly."
            }
