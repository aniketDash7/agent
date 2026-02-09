"""
BM25 sparse retrieval index.
"""
from rank_bm25 import BM25Okapi
import pickle
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 keyword-based search index."""
    
    def __init__(self, index_path: str = "bm25_index.pkl"):
        """Initialize BM25 index."""
        self.index_path = Path(index_path)
        self.bm25 = None
        self.documents = []
        self.metadatas = []
    
    def build_index(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """Build BM25 index from texts."""
        self.documents = texts
        self.metadatas = metadatas
        
        # Tokenize documents (simple whitespace tokenization)
        tokenized_docs = [doc.lower().split() for doc in texts]
        
        # Build BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
        
        logger.info(f"Built BM25 index with {len(texts)} documents")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search index with query."""
        if self.bm25 is None:
            logger.warning("BM25 index not built yet")
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only return non-zero scores
                results.append({
                    'text': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'score': float(scores[idx]),
                    'index': idx
                })
        
        return results
    
    def save(self):
        """Save index to disk."""
        data = {
            'bm25': self.bm25,
            'documents': self.documents,
            'metadatas': self.metadatas
        }
        
        with open(self.index_path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved BM25 index to {self.index_path}")
    
    def load(self):
        """Load index from disk."""
        if not self.index_path.exists():
            logger.warning(f"Index file {self.index_path} not found")
            return False
        
        with open(self.index_path, 'rb') as f:
            data = pickle.load(f)
        
        self.bm25 = data['bm25']
        self.documents = data['documents']
        self.metadatas = data['metadatas']
        
        logger.info(f"Loaded BM25 index from {self.index_path}")
        return True
