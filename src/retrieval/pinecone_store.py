"""
CapitalMind — Pinecone Vector Store.
Handles embedding upserts and similarity search with namespace-per-ticker.
"""
from __future__ import annotations
import os
import asyncio
from typing import Any
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from src.utils.settings import get_settings

settings = get_settings()

class PineconeVectorStore:
    """Pinecone Serverless vector store for financial document chunks."""

    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.pc = None
        self.index = None
        
        api_key = settings.pinecone_api_key.get_secret_value()
        if api_key:
            try:
                self.pc = Pinecone(api_key=api_key)
                self.index_name = settings.pinecone_index
                # Create index if it doesn't exist
                if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=settings.embedding_dim,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1")
                    )
                self.index = self.pc.Index(self.index_name)
            except Exception as e:
                print(f"Pinecone initialization failed: {e}")

    async def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        namespace: str,
    ) -> int:
        """Embed and upsert document chunks."""
        if not chunks: return 0
        
        texts = [c["text"] for c in chunks]
        # Generate embeddings via Ollama (this might be slow locally)
        embs = await self.embeddings.aembed_documents(texts)
        
        if self.index:
            vectors = []
            for i, (chunk, emb) in enumerate(zip(chunks, embs)):
                vectors.append({
                    "id": f"{namespace}_{i}_{id(chunk)}",
                    "values": emb,
                    "metadata": {
                        "text": chunk["text"],
                        "source": chunk.get("source", ""),
                        "ticker": namespace
                    }
                })
            
            # Batch upsert
            self.index.upsert(vectors=vectors, namespace=namespace)
            return len(vectors)
        
        # Fallback: In-memory mock search (for demo without API key)
        # Store chunks in a temporary attribute if index is missing
        if not hasattr(self, "_temp_storage"):
            self._temp_storage = {}
        self._temp_storage.setdefault(namespace, []).extend([
            {"text": c["text"], "emb": e, "source": c.get("source", "")}
            for c, e in zip(chunks, embs)
        ])
        return len(chunks)

    async def similarity_search(
        self,
        query: str,
        namespace: str,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        """Perform similarity search."""
        query_emb = await self.embeddings.aembed_query(query)
        
        if self.index:
            results = self.index.query(
                vector=query_emb,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )
            return [
                {"text": match.metadata["text"], "source": match.metadata.get("source", "")}
                for match in results.matches
            ]
        
        # Fallback: Simple cosine similarity if Pinecone is not configured
        if hasattr(self, "_temp_storage") and namespace in self._temp_storage:
            matches = []
            q_vec = np.array(query_emb)
            for item in self._temp_storage[namespace]:
                i_vec = np.array(item["emb"])
                score = np.dot(q_vec, i_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(i_vec))
                matches.append((score, item))
            
            matches.sort(key=lambda x: x[0], reverse=True)
            return [
                {"text": m[1]["text"], "source": m[1]["source"]}
                for m in matches[:top_k]
            ]
        
        return []
