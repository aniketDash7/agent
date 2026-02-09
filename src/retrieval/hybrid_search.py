"""
Hybrid search combining dense and sparse retrieval.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class HybridSearch:
    """Combine vector and keyword search with RRF."""
    
    def __init__(self, milvus_client, bm25_index, alpha: float = 0.7):
        """
        Initialize hybrid search.
        
        Args:
            milvus_client: Milvus vector database client
            bm25_index: BM25 sparse index
            alpha: Weight for dense vs sparse (0=all sparse, 1=all dense)
        """
        self.milvus = milvus_client
        self.bm25 = bm25_index
        self.alpha = alpha
    
    def search(self, query: str, query_embedding: List[float],
               top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform hybrid search."""
        # Dense search
        dense_results = self.milvus.search(query_embedding, top_k=top_k * 2)
        
        # Sparse search
        sparse_results = self.bm25.search(query, top_k=top_k * 2)
        
        # Reciprocal Rank Fusion
        merged_results = self._reciprocal_rank_fusion(
            dense_results, sparse_results, top_k
        )
        
        return merged_results
    
    def _reciprocal_rank_fusion(self, dense_results: List[Dict[str, Any]],
                                 sparse_results: List[Dict[str, Any]],
                                 top_k: int, k: int = 60) -> List[Dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion.
        
        Args:
            dense_results: Results from vector search
            sparse_results: Results from BM25
            top_k: Number of results to return
            k: Constant for RRF (typically 60)
        """
        # Create score dictionary
        scores = {}
        
        # Add dense scores
        for rank, result in enumerate(dense_results):
            text = result['text']
            rrf_score = self.alpha * (1.0 / (k + rank + 1))
            
            if text not in scores:
                scores[text] = {
                    'score': 0,
                    'text': text,
                    'metadata': result['metadata'],
                    'dense_score': result.get('score', 0),
                    'sparse_score': 0
                }
            
            scores[text]['score'] += rrf_score
            scores[text]['dense_score'] = result.get('score', 0)
        
        # Add sparse scores
        for rank, result in enumerate(sparse_results):
            text = result['text']
            rrf_score = (1 - self.alpha) * (1.0 / (k + rank + 1))
            
            if text not in scores:
                scores[text] = {
                    'score': 0,
                    'text': text,
                    'metadata': result['metadata'],
                    'dense_score': 0,
                    'sparse_score': result.get('score', 0)
                }
            
            scores[text]['score'] += rrf_score
            scores[text]['sparse_score'] = result.get('score', 0)
        
        # Sort by combined score
        sorted_results = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
        
        return sorted_results[:top_k]
