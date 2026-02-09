"""
Milvus vector database client.
"""
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from typing import List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class MilvusClient:
    """Client for Milvus vector database operations."""
    
    def __init__(self, host: str = "localhost", port: int = 19530,
                 collection_name: str = "document_chunks",
                 embedding_dim: int = 768):
        """Initialize Milvus client."""
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.collection = None
        
        # Connect to Milvus
        self._connect()
        
        # Create or load collection
        self._init_collection()
    
    def _connect(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def _init_collection(self):
        """Initialize collection with schema."""
        # Check if collection exists
        if utility.has_collection(self.collection_name):
            collection = Collection(self.collection_name)
            # Check dimension mismatch
            existing_dim = next(f.params['dim'] for f in collection.schema.fields if f.dtype == DataType.FLOAT_VECTOR)
            
            if existing_dim != self.embedding_dim:
                logger.warning(f"Dimension mismatch detected (existing: {existing_dim}, configured: {self.embedding_dim}). Dropping collection.")
                collection.drop()
                self._create_collection()
            else:
                self.collection = collection
                logger.info(f"Loaded existing collection: {self.collection_name}")
        else:
            self._create_collection()
        
        # Load collection into memory
        self.collection.load()
    
    def _create_collection(self):
        """Create new collection with schema."""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2000)
        ]
        
        schema = CollectionSchema(fields=fields, description="Document chunks with embeddings")
        self.collection = Collection(name=self.collection_name, schema=schema)
        
        # Create HNSW index for vector search
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        
        logger.info(f"Created new collection: {self.collection_name} with dim {self.embedding_dim}")
    
    def insert(self, embeddings: List[List[float]], texts: List[str],
               metadatas: List[Dict[str, Any]]) -> List[int]:
        """Insert vectors with text and metadata."""
        try:
            # Convert metadata to JSON strings
            metadata_strings = [json.dumps(m) for m in metadatas]
            
            entities = [
                embeddings,
                texts,
                metadata_strings
            ]
            
            insert_result = self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Inserted {len(texts)} chunks into Milvus")
            return insert_result.primary_keys
        
        except Exception as e:
            logger.error(f"Error inserting into Milvus: {e}")
            raise
    
    def search(self, query_embedding: List[float], top_k: int = 5,
               similarity_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        try:
            search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["text", "metadata"]
            )
            
            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    if hit.score >= similarity_threshold:
                        formatted_results.append({
                            'text': hit.entity.get('text'),
                            'metadata': json.loads(hit.entity.get('metadata')),
                            'score': hit.score,
                            'id': hit.id
                        })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching Milvus: {e}")
            raise
    
    def delete_all(self):
        """Delete all data from collection."""
        try:
            expr = "id > 0"
            self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"Deleted all data from {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting from Milvus: {e}")
            raise
    
    def get_count(self) -> int:
        """Get number of entities in collection."""
        self.collection.flush()
        return self.collection.num_entities
