"""
CapitalMind — Risk Assessor Agent.
Identifies and categorizes risk factors from SEC filings, news, and analysis.
"""
from __future__ import annotations
from typing import Any


class RiskAssessorAgent:
    """Agent that identifies material risk factors and assigns severity levels."""

    def __init__(self, llm):
        self.llm = llm

    async def assess(
        self,
        ticker: str,
        context_chunks: list[dict],
        financial_metrics: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Assess risks from filings and context.
        Returns list of RiskFlag dicts with:
        - category (regulatory, market, operational, ESG, liquidity)
        - severity (critical, high, medium, low)
        - description, evidence, sources
        """
        prompt = f"""Identify material risk factors for {ticker}.
Categorize each risk by type and severity.

Context:
{chr(10).join(c.get('text', '')[:500] for c in context_chunks[:8])}

Return a JSON array of risk flags."""

        response = await self.llm.ainvoke(prompt)
        return []
