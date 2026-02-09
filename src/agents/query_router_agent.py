"""
Query Router Agent - Routes queries based on complexity.
"""
from src.agents.base_agent import BaseAgent
from src.llm.prompt_templates import QUERY_ROUTER_PROMPT
from typing import Dict, Any


class QueryRouterAgent(BaseAgent):
    """Routes queries to appropriate processing pipeline."""
    
    def __init__(self, llm_client):
        super().__init__(llm_client, "QueryRouter")
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Classify query complexity."""
        self.log_thought("Analyzing query complexity")
        
        # Use LLM to classify
        prompt = QUERY_ROUTER_PROMPT.format(query=query)
        classification = self.llm.generate(prompt, temperature=0.1).strip().upper()
        
        # Parse classification
        if "SIMPLE" in classification:
            route = "simple"
        elif "COMPLEX" in classification:
            route = "complex"
        elif "CLARIFICATION" in classification:
            route = "clarification"
        else:
            # Default to simple if unclear
            route = "simple"
        
        self.log_thought(f"Query classified as: {route}")
        
        return {
            'route': route,
            'classification': classification
        }
