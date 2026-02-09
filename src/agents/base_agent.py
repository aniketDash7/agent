"""
Base agent class with logging and tool interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, llm_client, agent_name: str):
        """Initialize agent."""
        self.llm = llm_client
        self.agent_name = agent_name
        self.thought_log = []
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute agent's primary function."""
        pass
    
    def log_thought(self, thought: str, data: Any = None):
        """Log agent's reasoning step."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': self.agent_name,
            'thought': thought,
            'data': data
        }
        self.thought_log.append(log_entry)
        logger.info(f"[{self.agent_name}] {thought}")
    
    def get_thought_log(self) -> List[Dict[str, Any]]:
        """Get all logged thoughts."""
        return self.thought_log
    
    def clear_thought_log(self):
        """Clear thought log."""
        self.thought_log = []
