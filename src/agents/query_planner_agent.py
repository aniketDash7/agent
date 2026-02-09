"""
Query Planner Agent - Decomposes complex queries.
"""
from src.agents.base_agent import BaseAgent
from src.llm.prompt_templates import QUERY_PLANNER_PROMPT
from typing import Dict, Any, List
import re


class QueryPlannerAgent(BaseAgent):
    """Decomposes complex queries into sub-queries."""
    
    def __init__(self, llm_client):
        super().__init__(llm_client, "QueryPlanner")
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Decompose query into sub-queries."""
        self.log_thought("Decomposing complex query")
        
        # Use LLM to generate sub-queries
        prompt = QUERY_PLANNER_PROMPT.format(query=query)
        response = self.llm.generate(prompt, temperature=0.3)
        
        # Parse sub-queries
        sub_queries = self._parse_sub_queries(response)
        
        self.log_thought(f"Generated {len(sub_queries)} sub-queries", sub_queries)
        
        return {
            'sub_queries': sub_queries,
            'original_query': query
        }
    
    def _parse_sub_queries(self, response: str) -> List[str]:
        """Extract numbered sub-queries from response."""
        lines = response.strip().split('\n')
        sub_queries = []
        
        for line in lines:
            # Match numbered lines like "1. " or "1) "
            match = re.match(r'^\d+[\.\)]\s*(.+)$', line.strip())
            if match:
                sub_queries.append(match.group(1).strip())
        
        # If no numbered format found, split by newlines
        if not sub_queries:
            sub_queries = [line.strip() for line in lines if line.strip()]
        
        return sub_queries
