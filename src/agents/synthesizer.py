"""
CapitalMind — Synthesizer Agent.
Combines all analysis outputs into a structured investment research memo
with inline citations and confidence scoring.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage


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
        Returns: (draft_memo: str, overall_confidence: float)
        """
        
        system_prompt = """You are a Lead Investment Strategist at a top-tier hedge fund.
Your goal is to synthesize multiple specialized agent reports into a single, cohesive, 
and institutional-quality investment research memo.
Use professional tone, Markdown formatting, and ensure clear section headers."""

        data_summary = {
            "ticker": ticker,
            "company": company_name,
            "research_type": research_type,
            "market_snapshot": market_snapshot,
            "financials": financial_metrics,
            "sentiment": sentiment_signals,
            "risks": risk_flags,
            "peers": peer_comparison,
            "charts": chart_interpretations,
        }

        user_prompt = f"""Generate a comprehensive investment research memo for {company_name} ({ticker}).

Input Data:
{json.dumps(data_summary, indent=2)}

Memo Structure:
1. Executive Summary: High-level thesis and recommendation.
2. Market & Valuation: Snapshot of current market position.
3. Financial Performance: Key revenue drives, margins, and EPS trends.
4. Qualitative Insights: Sentiment from transcripts and management tone.
5. Risk Assessment: Categorized risks and potential headwinds.
6. Investment Conclusion: Final verdict and outlook.

Cite specific metrics and evidence provided in the data. 
Use tables for financial comparisons where possible."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            draft = response.content
            
            # Simple heuristic for confidence based on data availability
            metrics_count = sum(1 for v in (financial_metrics or {}).values() if v is not None)
            base_confidence = 0.6 + (metrics_count / 13) * 0.3
            if sentiment_signals: base_confidence += 0.05
            if risk_flags: base_confidence += 0.05
            
            return draft, min(0.99, base_confidence)
            
        except Exception as e:
            return f"Error during synthesis: {str(e)}", 0.0
