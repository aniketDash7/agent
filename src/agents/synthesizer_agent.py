"""
Synthesizer Agent - Generates answers with citations.
"""
from src.agents.base_agent import BaseAgent
from src.llm.prompt_templates import SYNTHESIZER_PROMPT
from typing import Dict, Any, List


class SynthesizerAgent(BaseAgent):
    """Synthesizes answer from retrieved context."""
    
    def __init__(self, llm_client):
        super().__init__(llm_client, "Synthesizer")
    
    def execute(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer from context."""
        self.log_thought("Synthesizing answer from context")
        
        # Format context
        context = self._format_context(retrieved_docs)
        
        # Generate answer
        prompt = SYNTHESIZER_PROMPT.format(
            query=query,
            context=context
        )
        
        answer = self.llm.generate(prompt, temperature=0.3)
        
        self.log_thought("Answer generated with citations")
        
        return {
            'answer': answer,
            'sources': self._extract_sources(retrieved_docs),
            'context': context
        }
    
    def _format_context(self, docs: List[Dict[str, Any]]) -> str:
        """Format documents as context."""
        context_parts = []
        
        for i, doc in enumerate(docs):
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            
            # Add page/slide info if available
            location = ""
            if 'page' in metadata:
                location = f", page {metadata['page']}"
            elif 'slide' in metadata:
                location = f", slide {metadata['slide']}"
            elif 'sheet' in metadata:
                location = f", sheet {metadata['sheet']}"
            
            context_parts.append(
                f"[Source {i+1}: {source}{location}]\n{doc['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information."""
        sources = []
        
        for doc in docs:
            metadata = doc.get('metadata', {})
            sources.append({
                'source': metadata.get('source', 'Unknown'),
                'page': metadata.get('page'),
                'slide': metadata.get('slide'),
                'sheet': metadata.get('sheet'),
                'file_type': metadata.get('file_type')
            })
        
        return sources
