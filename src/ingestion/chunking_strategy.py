"""
Intelligent text chunking strategies.
"""
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk text intelligently with overlap."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 128,
                 separators: List[str] = None):
        """Initialize chunker with parameters."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_document(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk a loaded document."""
        all_chunks = []
        
        for chunk in doc_data['chunks']:
            text = chunk['text']
            metadata = chunk['metadata']
            
            # Chunk the text
            text_chunks = self._recursive_split(text)
            
            # Add metadata to each chunk
            for i, text_chunk in enumerate(text_chunks):
                chunk_dict = {
                    'text': text_chunk,
                    'metadata': {
                        **metadata,
                        'chunk_index': i,
                        'total_chunks': len(text_chunks)
                    }
                }
                all_chunks.append(chunk_dict)
        
        return all_chunks
    
    def _recursive_split(self, text: str) -> List[str]:
        """Recursively split text using separators."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        # Try each separator
        for separator in self.separators:
            if separator == "":
                # Character-level split
                return self._character_split(text)
            
            if separator in text:
                splits = text.split(separator)
                return self._merge_splits(splits, separator)
        
        # Fallback to character split
        return self._character_split(text)
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits into chunks of appropriate size with overlap."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for split in splits:
            split_size = len(split)
            
            if current_size + split_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(separator.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_text = separator.join(current_chunk)
                if len(overlap_text) > self.chunk_overlap:
                    # Keep only last parts for overlap
                    overlap_splits = current_chunk[-2:] if len(current_chunk) > 1 else current_chunk[-1:]
                    current_chunk = overlap_splits
                    current_size = sum(len(s) for s in overlap_splits)
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(split)
            current_size += split_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(separator.join(current_chunk))
        
        return chunks
    
    def _character_split(self, text: str) -> List[str]:
        """Split text at character level with overlap."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
        
        return chunks
