"""
CapitalMind — Sentiment Analyst Agent.
Analyzes tone, guidance, and hedging signals in management commentary.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage


class SentimentAnalystAgent:
    """Agent that performs sentiment and tone analysis on transcripts/filings."""

    def __init__(self, llm):
        self.llm = llm

    async def analyze(
        self,
        ticker: str,
        context_chunks: list[dict],
        market_snapshot: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze sentiment signals and return SentimentSignal list.
        """
        context_text = "\n\n".join([
             f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}"
             for c in context_chunks[:15]
        ])

        system_prompt = """You are an expert Equity Research Analyst. 
Analyze the following management commentary for tone, future guidance, and hedging.
Identify specific 'signals' (positive or negative) with quotes."""

        user_prompt = f"""Ticker: {ticker}

Context Data:
{context_text[:12000]}

Extract 3-5 key sentiment signals from the management commentary.
Return JSON format:
[
  {{
    "source": "TRANSCRIPT" or "Earnings Call",
    "label": "positive" | "negative" | "neutral",
    "score": float (-1.0 to 1.0),
    "confidence": float (0.0 to 1.0),
    "description": "Short explanation",
    "evidence_quote": "Exact quote from text"
  }}
]"""

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
            
            return json.loads(content)
            
        except Exception:
            return []
