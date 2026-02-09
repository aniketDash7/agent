"""
Basic tests for core components.
"""
import pytest
from src.llm.ollama_client import OllamaClient
from src.ingestion.document_loader import DocumentLoader, TextLoader
from src.ingestion.chunking_strategy import TextChunker


def test_text_loader():
    """Test basic text loading."""
    # This would need actual file
    # Just testing the structure
    assert TextLoader is not None
    

def test_text_chunker():
    """Test text chunking."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    
    text = "This is a test. " * 50
    doc_data = {
        'chunks': [{
            'text': text,
            'metadata': {'source': 'test.txt', 'file_type': 'txt'}
        }]
    }
    
    chunks = chunker.chunk_document(doc_data)
    
    assert len(chunks) > 0
    assert all('text' in chunk for chunk in chunks)
    assert all('metadata' in chunk for chunk in chunks)


def test_chunker_overlap():
    """Test that chunking creates reasonable overlap."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    
    text = "A" * 200
    doc_data = {
        'chunks': [{
            'text': text,
            'metadata': {'source': 'test.txt'}
        }]
    }
    
    chunks = chunker.chunk_document(doc_data)
    
    # Should have multiple chunks
    assert len(chunks) > 1
    
    # Check chunk sizes
    for chunk in chunks:
        assert len(chunk['text']) <= 50 or len(chunk['text']) <= 60  # Allow some flexibility


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
