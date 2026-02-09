"""
Retriever Agent - Adaptive document retrieval with self-reflection.
"""
from src.agents.base_agent import BaseAgent
from src.llm.prompt_templates import RETRIEVER_ANALYSIS_PROMPT, QUERY_EXPANSION_PROMPT
from typing import Dict, Any, List
import re


class RetrieverAgent(BaseAgent):
    """Retrieves documents with adaptive strategy."""
    
    def __init__(self, llm_client, hybrid_search, quality_threshold: float = 0.5):
        super().__init__(llm_client, "Retriever")
        self.hybrid_search = hybrid_search
        self.quality_threshold = quality_threshold
    
    def execute(self, query: str, top_k: int = 5, 
                max_retries: int = 2) -> Dict[str, Any]:
        """Retrieve documents with self-reflection."""
        self.log_thought(f"Retrieving documents for query")
        
        # Initial retrieval
        query_embedding = self.llm.generate_embedding(query)
        results = self.hybrid_search.search(query, query_embedding, top_k=top_k)
        
        # Self-reflection: Are results good enough?
        confidence = self._evaluate_results(query, results)
        
        self.log_thought(f"Initial retrieval confidence: {confidence:.2f}")
        
        # If low confidence and retries available, try query expansion
        if confidence < self.quality_threshold and max_retries > 0:
            self.log_thought("Low confidence, attempting query expansion")
            expanded_results = self._retrieve_with_expansion(query, top_k, max_retries - 1)
            
            # Compare confidence
            expanded_confidence = self._evaluate_results(query, expanded_results)
            
            if expanded_confidence > confidence:
                self.log_thought(f"Expansion improved confidence to {expanded_confidence:.2f}")
                results = expanded_results
                confidence = expanded_confidence
        
        return {
            'results': results,
            'confidence': confidence,
            'query': query
        }
    
    def _evaluate_results(self, query: str, results: List[Dict[str, Any]]) -> float:
        """Evaluate quality of retrieved results."""
        if not results:
            return 0.0
        
        # Format documents for LLM
        docs_text = "\n\n".join([
            f"[Doc {i+1}] {r['text'][:300]}..."
            for i, r in enumerate(results[:3])
        ])
        
        # Use LLM to evaluate
        prompt = RETRIEVER_ANALYSIS_PROMPT.format(
            query=query,
            documents=docs_text
        )
        
        try:
            response = self.llm.generate(prompt, temperature=0.1)
            
            # Parse confidence score
            match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response)
            if match:
                confidence = float(match.group(1))
                return confidence
        except:
            pass
        
        # Fallback: use average similarity score
        avg_score = sum(r.get('score', 0) for r in results) / len(results)
        return avg_score
    
    def _retrieve_with_expansion(self, query: str, top_k: int, 
                                   max_retries: int) -> List[Dict[str, Any]]:
        """Retrieve with query expansion."""
        # Generate expanded queries
        prompt = QUERY_EXPANSION_PROMPT.format(query=query)
        response = self.llm.generate(prompt, temperature=0.5)
        
        # Parse expanded queries
        expanded_queries = [query]  # Include original
        lines = response.strip().split('\n')
        for line in lines:
            match = re.match(r'^\d+[\.\)]\s*(.+)$', line.strip())
            if match:
                expanded_queries.append(match.group(1).strip())
        
        self.log_thought(f"Expanded into {len(expanded_queries)} queries")
        
        # Retrieve for each expanded query
        all_results = {}
        for exp_query in expanded_queries[:3]:  # Limit to 3 expansions
            query_embedding = self.llm.generate_embedding(exp_query)
            results = self.hybrid_search.search(exp_query, query_embedding, top_k=top_k)
            
            # Merge results (deduplicate by text)
            for r in results:
                text = r['text']
                if text not in all_results or r['score'] > all_results[text]['score']:
                    all_results[text] = r
        
        # Return top-k by score
        merged = sorted(all_results.values(), key=lambda x: x['score'], reverse=True)
        return merged[:top_k]
