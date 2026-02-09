"""
Validator Agent - Quality control with self-reflection.
"""
from src.agents.base_agent import BaseAgent
from src.llm.prompt_templates import VALIDATOR_PROMPT
from typing import Dict, Any
import re


class ValidatorAgent(BaseAgent):
    """Validates answer quality and consistency."""
    
    def __init__(self, llm_client, quality_threshold: float = 0.7):
        super().__init__(llm_client, "Validator")
        self.quality_threshold = quality_threshold
    
    def execute(self, query: str, answer: str, context: str) -> Dict[str, Any]:
        """Validate answer quality."""
        self.log_thought("Validating answer quality")
        
        # Use LLM to evaluate
        prompt = VALIDATOR_PROMPT.format(
            query=query,
            answer=answer,
            context=context
        )
        
        response = self.llm.generate(prompt, temperature=0.1)
        
        # Parse validation results
        validation = self._parse_validation(response)
        
        # Determine if answer passes
        passed = validation['quality_score'] >= self.quality_threshold
        
        if passed:
            self.log_thought(f"✓ Answer passed validation (score: {validation['quality_score']:.2f})")
        else:
            self.log_thought(f"✗ Answer failed validation (score: {validation['quality_score']:.2f})")
            self.log_thought(f"Issues: {validation.get('issues', 'Unknown')}")
        
        return {
            'passed': passed,
            'validation': validation,
            'score': validation['quality_score']
        }
    
    def _parse_validation(self, response: str) -> Dict[str, Any]:
        """Parse validation response."""
        validation = {
            'addresses_query': False,
            'factually_consistent': False,
            'properly_cited': False,
            'quality_score': 0.0,
            'issues': ''
        }
        
        # Parse each field
        patterns = {
            'addresses_query': r'ADDRESSES_QUERY:\s*(YES|NO)',
            'factually_consistent': r'FACTUALLY_CONSISTENT:\s*(YES|NO)',
            'properly_cited': r'PROPERLY_CITED:\s*(YES|NO)',
            'quality_score': r'QUALITY_SCORE:\s*([0-9.]+)',
            'issues': r'ISSUES:\s*(.+?)(?:\n|$)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key in ['addresses_query', 'factually_consistent', 'properly_cited']:
                    validation[key] = value.upper() == 'YES'
                elif key == 'quality_score':
                    validation[key] = float(value)
                else:
                    validation[key] = value
        
        return validation
