from src.agents.base_agent import BaseAgent

class RerankerAgent(BaseAgent):
    def __init__(self, llm_client, top_k=3):
        super().__init__(llm_client, "Reranker")
        self.top_k = top_k
        
    def execute(self, query, docs):
        self.log_thought(f"Reranking {len(docs)} documents for query: '{query}'")
        
        for doc in docs:
            prompt = f"Rate the relevance of the following document to the given query on a strict scale of 0.0 to 1.0. Output ONLY the floating point number and nothing else.\n\nQuery: {query}\n\nDocument: {doc.get('text', '')}\n\nRelevance Score (0.0 - 1.0):"
            response = self.llm.generate(prompt, temperature=0.0).strip()
            
            try:
                doc['rerank_score'] = float(response)
            except Exception as e:
                self.log_thought(f"Failed to parse rerank score '{response}': {e}. Falling back to average score.")
                doc['rerank_score'] = doc.get('score', 0.0)
                
        sorted_docs = sorted(docs, key=lambda x: x.get('rerank_score', 0.0), reverse=True)
        return sorted_docs[:self.top_k]
