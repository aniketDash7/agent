"""
CapitalMind — Fact Checker Agent.
Verifies claims in the synthesized memo against original document sources.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage


class FactCheckerAgent:
    """Agent that cross-references memo claims against source documents."""

    def __init__(self, llm):
        self.llm = llm

    async def verify(
        self,
        draft_memo: str,
        context_chunks: list[dict],
    ) -> dict[str, Any]:
        """
        Verify claims and return a verification report.
        """
        context_text = "\n\n".join([
             f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}"
             for c in context_chunks[:20]
        ])

        system_prompt = """You are a professional Fact-Checker. 
Your task is to identify and verify every specific factual claim (numbers, dates, percentages) 
in the investment memo against the source data provided.
Flag contradictions, inaccuracies, or hallucinations."""

        user_prompt = f"""Investment Memo Draft:
{draft_memo}

Source Data:
{context_text[:15000]}

Verify each claim. Return JSON format:
{{
  "claims": [
    {{
      "claim": "string",
      "status": "verified" | "contradicted" | "unsupported",
      "evidence": "supporting text from source",
      "correction": "correct value if contradicted, else null"
    }}
  ],
  "overall_accuracy_score": float (0.0 to 1.0),
  "warnings": ["string"]
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
            
            return json.loads(content)
            
        except Exception as e:
            return {
                "claims": [],
                "overall_accuracy_score": 0.0,
                "warnings": [f"Fact-check failed: {str(e)}"]
            }
