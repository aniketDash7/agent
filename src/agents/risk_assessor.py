"""
CapitalMind — Risk Assessor Agent.
Identifies and categorizes risk flags from legal and management disclosures.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage


class RiskAssessorAgent:
    """Agent that extracts and categorizes risk factors from SEC filings."""

    def __init__(self, llm):
        self.llm = llm

    async def analyze(
        self,
        ticker: str,
        context_chunks: list[dict],
    ) -> list[dict[str, Any]]:
        """
        Identify risk flags and return RiskFlag list.
        """
        context_text = "\n\n".join([
             f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}"
             for c in context_chunks[:15]
        ])

        system_prompt = """You are a Risk Management Consultant. 
Identify the top risk factors for the company based on the provided disclosures.
Categorize them as macro, operational, financial, or regulatory."""

        user_prompt = f"""Ticker: {ticker}

Context Data:
{context_text[:12000]}

Extract 3-5 significant risk flags.
Return JSON format:
[
  {{
    "run_id": "...",
    "ticker": "{ticker}",
    "category": "macro" | "operational" | "financial" | "regulatory",
    "severity": "critical" | "high" | "medium" | "low",
    "description": "Detailed risk description",
    "evidence": ["Quote 1", "Quote 2"],
    "mitigation_noted": boolean
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
