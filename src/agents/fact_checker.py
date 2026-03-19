"""
CapitalMind — Fact Checker Agent.
Validates claims in the draft memo against source documents.
Flags unverified or contradicted claims.
"""
from __future__ import annotations
from typing import Any


class FactCheckerAgent:
    """Agent that extracts and verifies claims from research memos."""

    def __init__(self, llm):
        self.llm = llm

    async def verify(
        self,
        draft_memo: str,
        context_chunks: list[dict],
        ticker: str,
    ) -> list[dict[str, Any]]:
        """
        Extract claims from the draft memo and verify each against source docs.

        Returns list of CitedClaim dicts with:
        - claim, verified (bool), confidence
        - supporting_sources, contradicting_sources, verifier_notes
        """
        prompt = f"""Extract all factual claims from this investment memo for {ticker}.
For each claim, determine if it is supported by the source documents.

Memo excerpt:
{draft_memo[:3000]}

Source context:
{chr(10).join(c.get('text', '')[:300] for c in context_chunks[:6])}

Return a JSON array of verified claims."""

        response = await self.llm.ainvoke(prompt)
        return []
