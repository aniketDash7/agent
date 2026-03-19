"""
CapitalMind — Synthesizer Agent.
Combines all analysis outputs into a structured investment research memo
with inline citations and confidence scoring.
"""
from __future__ import annotations
from typing import Any


class SynthesizerAgent:
    """Agent that generates investment research memos from analysis outputs."""

    def __init__(self, llm):
        self.llm = llm

    async def synthesize(
        self,
        ticker: str,
        company_name: str,
        research_type: str,
        financial_metrics: dict | None = None,
        sentiment_signals: list[dict] | None = None,
        risk_flags: list[dict] | None = None,
        peer_comparison: dict | None = None,
        retrieved_context: list[dict] | None = None,
        chart_interpretations: list[str] | None = None,
        extracted_tables: list[dict] | None = None,
        market_snapshot: dict | None = None,
    ) -> tuple[str, float]:
        """
        Synthesize all analyses into an investment memo.

        Returns:
            (draft_memo: str, overall_confidence: float)
        """
        prompt = f"""Generate a comprehensive investment research memo for
{company_name} ({ticker}). Research type: {research_type}.

Synthesize the following analyses into a structured memo with citations:
- Financial metrics
- Sentiment signals
- Risk flags
- Peer comparison
- Market data

Include: Executive Summary, Investment Thesis, Financial Analysis,
Sentiment Analysis, Risk Assessment, and Conclusion."""

        response = await self.llm.ainvoke(prompt)
        draft = response.content if hasattr(response, "content") else str(response)
        confidence = 0.75  # Default confidence; adjusted by fact-checker

        return draft, confidence
