"""
Agent Orchestrator - Coordinates multi-agent workflow.
"""
from src.agents.query_router_agent import QueryRouterAgent
from src.agents.query_planner_agent import QueryPlannerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.synthesizer_agent import SynthesizerAgent
from src.agents.validator_agent import ValidatorAgent
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates the multi-agent RAG workflow."""
    
    def __init__(self, llm_client, hybrid_search, config: Dict[str, Any]):
        """Initialize orchestrator with all agents."""
        self.llm = llm_client
        self.config = config
        
        # Initialize agents
        self.router = QueryRouterAgent(llm_client)
        self.planner = QueryPlannerAgent(llm_client)
        self.retriever = RetrieverAgent(
            llm_client, 
            hybrid_search,
            quality_threshold=config.get('agents', {}).get('quality_threshold', 0.5)
        )
        self.synthesizer = SynthesizerAgent(llm_client)
        self.validator = ValidatorAgent(
            llm_client,
            quality_threshold=config.get('agents', {}).get('quality_threshold', 0.7)
        )
        
        self.max_iterations = config.get('agents', {}).get('max_iterations', 3)
        self.activity_log = []
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query through agentic workflow."""
        self.activity_log = []
        self._log_activity("Starting query processing", "system")
        
        # Step 1: Route query
        routing = self.router.execute(query)
        self._log_activity(f"Query routed as: {routing['route']}", "router")
        
        # Step 2: Handle based on route
        if routing['route'] == 'complex':
            result = self._handle_complex_query(query)
        elif routing['route'] == 'clarification':
            result = self._handle_clarification(query)
        else:
            result = self._handle_simple_query(query)
        
        # Add activity log to result
        result['activity_log'] = self.activity_log
        result['all_thoughts'] = self._collect_all_thoughts()
        
        return result
    
    def _handle_simple_query(self, query: str) -> Dict[str, Any]:
        """Handle simple direct query."""
        self._log_activity("Processing as simple query", "orchestrator")
        
        # Retrieve -> Synthesize -> Validate loop
        for iteration in range(self.max_iterations):
            # Retrieve
            retrieval_result = self.retriever.execute(query)
            self._log_activity(
                f"Retrieved {len(retrieval_result['results'])} documents " 
                f"(confidence: {retrieval_result['confidence']:.2f})",
                "retriever"
            )
            
            # Synthesize
            synthesis = self.synthesizer.execute(query, retrieval_result['results'])
            self._log_activity("Generated answer with citations", "synthesizer")
            
            # Validate
            validation = self.validator.execute(
                query, 
                synthesis['answer'],
                synthesis['context']
            )
            self._log_activity(
                f"Validation score: {validation['score']:.2f}",
                "validator"
            )
            
            # If validation passed, return
            if validation['passed']:
                self._log_activity("✓ Answer approved", "validator")
                return {
                    'success': True,
                    'answer': synthesis['answer'],
                    'sources': synthesis['sources'],
                    'confidence': retrieval_result['confidence'],
                    'validation': validation,
                    'iterations': iteration + 1
                }
            else:
                self._log_activity(
                    f"✗ Validation failed (iteration {iteration + 1})",
                    "validator"
                )
        
        # Max iterations reached
        self._log_activity("Max iterations reached, returning best attempt", "orchestrator")
        return {
            'success': False,
            'answer': synthesis['answer'],
            'sources': synthesis['sources'],
            'confidence': retrieval_result['confidence'],
            'validation': validation,
            'iterations': self.max_iterations,
            'note': 'Answer quality below threshold but max iterations reached'
        }
    
    def _handle_complex_query(self, query: str) -> Dict[str, Any]:
        """Handle complex multi-part query."""
        self._log_activity("Processing as complex query", "orchestrator")
        
        # Decompose query
        plan = self.planner.execute(query)
        sub_queries = plan['sub_queries']
        self._log_activity(f"Decomposed into {len(sub_queries)} sub-queries", "planner")
        
        # Process each sub-query
        sub_results = []
        for i, sub_query in enumerate(sub_queries):
            self._log_activity(f"Processing sub-query {i+1}: {sub_query}", "orchestrator")
            result = self._handle_simple_query(sub_query)
            sub_results.append({
                'sub_query': sub_query,
                'answer': result.get('answer', ''),
                'sources': result.get('sources', [])
            })
        
        # Combine results
        combined_context = "\n\n".join([
            f"Sub-query: {r['sub_query']}\nAnswer: {r['answer']}"
            for r in sub_results
        ])
        
        # Synthesize final answer
        final_synthesis = self.synthesizer.execute(query, [])
        
        # Use LLM to combine sub-answers
        combine_prompt = f"""Given these sub-answers, provide a comprehensive answer to the original query.

Original Query: {query}

Sub-answers:
{combined_context}

Synthesized Answer:"""
        
        final_answer = self.llm.generate(combine_prompt, temperature=0.3)
        
        self._log_activity("Combined sub-answers into final response", "synthesizer")
        
        # Collect all sources
        all_sources = []
        for r in sub_results:
            all_sources.extend(r['sources'])
        
        return {
            'success': True,
            'answer': final_answer,
            'sources': all_sources,
            'sub_results': sub_results,
            'query_type': 'complex'
        }
    
    def _handle_clarification(self, query: str) -> Dict[str, Any]:
        """Handle ambiguous query."""
        self._log_activity("Query needs clarification", "router")
        
        clarification_prompt = f"""The query is ambiguous. Provide:
1. A polite request for clarification
2. 2-3 specific questions to help narrow down the intent

Query: {query}"""
        
        clarification = self.llm.generate(clarification_prompt, temperature=0.5)
        
        return {
            'success': False,
            'needs_clarification': True,
            'clarification_request': clarification,
            'query_type': 'clarification'
        }
    
    def _log_activity(self, message: str, agent: str):
        """Log activity for UI display."""
        activity = {
            'agent': agent,
            'message': message
        }
        self.activity_log.append(activity)
        logger.info(f"[{agent}] {message}")
    
    def _collect_all_thoughts(self) -> List[Dict[str, Any]]:
        """Collect thoughts from all agents."""
        all_thoughts = []
        for agent in [self.router, self.planner, self.retriever, 
                      self.synthesizer, self.validator]:
            all_thoughts.extend(agent.get_thought_log())
        return all_thoughts
