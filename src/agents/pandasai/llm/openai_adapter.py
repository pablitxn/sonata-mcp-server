"""OpenAI/OpenRouter/Ollama LLM adapter for PandasAI"""

import os
from typing import Optional, Any
import httpx
import json

from ..agent.state import AgentState
from ..core.prompts.base import BasePrompt
from .base import LLM


class ConfigurableLLM(LLM):
    """LLM adapter that works with OpenAI, OpenRouter, and Ollama based on environment configuration"""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize the LLM based on environment configuration"""
        # Get LLM provider and configuration from environment
        self.provider = os.getenv('LLM_PROVIDER', 'openai')
        self.model = os.getenv('LLM_CHOICE', 'gpt-4o-mini')
        self.base_url = os.getenv('LLM_BASE_URL')
        
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.getenv('LLM_API_KEY')
            # Fallback to OPENAI_API_KEY if LLM_API_KEY is not set
            if not api_key and self.provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
            
        if not api_key:
            raise ValueError(f"API key not found for provider {self.provider}. "
                           f"Please set LLM_API_KEY or OPENAI_API_KEY environment variable.")
            
        super().__init__(api_key=api_key, **kwargs)
        
        # Set up provider-specific configurations
        if self.provider == 'openai':
            self.api_endpoint = "https://api.openai.com/v1/chat/completions"
        elif self.provider == 'openrouter':
            self.api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
            # OpenRouter needs a specific header
            self.extra_headers = {"X-API-Key": self.api_key}
        elif self.provider == 'ollama':
            # Use base URL or default to localhost
            base = self.base_url or "http://localhost:11434"
            self.api_endpoint = f"{base}/api/chat"
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    @property
    def type(self) -> str:
        """Return the type of LLM"""
        return f"{self.provider}-{self.model}"

    def call(self, instruction: BasePrompt, context: AgentState = None) -> str:
        """Execute the LLM with given prompt"""
        self.last_prompt = instruction.to_string()
        
        if self.provider == 'ollama':
            return self._call_ollama(instruction, context)
        else:
            return self._call_openai_compatible(instruction, context)

    def _call_openai_compatible(self, instruction: BasePrompt, context: AgentState = None) -> str:
        """Call OpenAI-compatible API (OpenAI or OpenRouter)"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Add extra headers for OpenRouter
        if self.provider == 'openrouter' and hasattr(self, 'extra_headers'):
            headers.update(self.extra_headers)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes data and generates Python code to answer questions about dataframes."},
            {"role": "user", "content": instruction.to_string()}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        with httpx.Client() as client:
            response = client.post(
                self.api_endpoint,
                headers=headers,
                json=data,
                timeout=60.0
            )
            response.raise_for_status()
            
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_ollama(self, instruction: BasePrompt, context: AgentState = None) -> str:
        """Call Ollama API"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes data and generates Python code to answer questions about dataframes."},
            {"role": "user", "content": instruction.to_string()}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2000
            }
        }
        
        with httpx.Client() as client:
            response = client.post(
                self.api_endpoint,
                json=data,
                timeout=120.0  # Ollama can be slower
            )
            response.raise_for_status()
            
        result = response.json()
        return result["message"]["content"]