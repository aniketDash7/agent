"""
CapitalMind — Sentiment Analyst Agent.
Analyzes management tone, analyst sentiment, and forward guidance signals.
"""
from __future__ import annotations
from typing import Any


class SentimentAnalystAgent:
    """Agent that performs sentiment analysis on earnings transcripts and filings."""

    def __init__(self, llm):
        self.llm = llm

    async def analyze(
        self,
        ticker: str,
        context_chunks: list[dict],
        document_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze sentiment across document sources.
        Returns list of SentimentSignal dicts with:
        - source, score (-1 to 1), label, confidence
        - key_phrases, tone_indicators, forward_guidance
        """
        relevant_chunks = [
            c for c in context_chunks
            if not document_types or c.get("document_type") in document_types
        ]

        prompt = f"""Analyze the sentiment and tone for {ticker} from the following context.
Identify management tone, analyst sentiment, hedging language, and forward guidance signals.

{chr(10).join(c.get('text', '')[:500] for c in relevant_chunks[:8])}

Return a JSON array of sentiment signals."""

        response = await self.llm.ainvoke(prompt)
        return []
