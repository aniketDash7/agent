"""
Ollama client for LLM and embedding generation.
"""
import ollama
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", 
                 llm_model: str = "llama3.2:3b",
                 embedding_model: str = "mxbai-embed-large",
                 temperature: float = 0.7):
        """Initialize Ollama client."""
        self.base_url = base_url
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.client = ollama.Client(host=base_url)
    
    def generate(self, prompt: str, system: Optional[str] = None,
                 stream: bool = False, **kwargs) -> str:
        """Generate text using LLM."""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            # Use provided temperature or default
            if 'temperature' not in kwargs:
                kwargs['temperature'] = self.temperature
                
            response = self.client.chat(
                model=self.llm_model,
                messages=messages,
                stream=stream,
                options=kwargs
            )
            
            if stream:
                return response
            else:
                return response['message']['content']
        
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            response = self.client.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response['embedding']
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def check_model_availability(self) -> Dict[str, bool]:
        """Check if required models are available."""
        try:
            models = self.client.list()
            model_names = [m['name'] for m in models['models']]
            
            return {
                'llm': self.llm_model in model_names,
                'embedding': self.embedding_model in model_names
            }
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return {'llm': False, 'embedding': False}
