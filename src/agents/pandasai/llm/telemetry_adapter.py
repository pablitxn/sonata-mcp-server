"""OpenAI/OpenRouter/Ollama LLM adapter with telemetry integration for PandasAI"""

import os
import time
from typing import Optional, Any, Dict
import httpx
import json

from ..agent.state import AgentState
from ..core.prompts.base import BasePrompt
from .base import LLM
from config.telemetry_logger import logger, get_telemetry
from telemetry.interfaces import SpanKind


class TelemetryLLM(LLM):
    """LLM adapter with comprehensive telemetry tracking for MCP visibility"""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize the LLM with telemetry support"""
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
        
        # Initialize telemetry
        self.telemetry = get_telemetry()
        self.tracer = self.telemetry.get_tracer() if self.telemetry else None
        self.llm_telemetry = self.telemetry.get_llm_telemetry() if self.telemetry else None
        
        logger.info(
            "initialized_telemetry_llm",
            provider=self.provider,
            model=self.model,
            telemetry_enabled=bool(self.telemetry)
        )

    @property
    def type(self) -> str:
        """Return the type of LLM"""
        return f"{self.provider}-{self.model}"

    def call(self, instruction: BasePrompt, context: AgentState = None) -> str:
        """Execute the LLM with comprehensive telemetry tracking"""
        self.last_prompt = instruction.to_string()
        
        # Start telemetry span
        with self._create_llm_span(instruction, context) as span_data:
            try:
                if self.provider == 'ollama':
                    response = self._call_ollama_with_telemetry(instruction, context, span_data)
                else:
                    response = self._call_openai_compatible_with_telemetry(instruction, context, span_data)
                
                # Track successful generation
                self._track_generation_success(instruction, response, span_data)
                
                return response
                
            except Exception as e:
                # Track error
                self._track_generation_error(instruction, e, span_data)
                raise

    def _create_llm_span(self, instruction: BasePrompt, context: AgentState = None):
        """Create a telemetry span for LLM operations"""
        if self.llm_telemetry:
            # Extract metadata from context
            metadata = {
                "provider": self.provider,
                "model": self.model,
                "operation": "pandasai_code_generation",
                "prompt_type": instruction.__class__.__name__,
            }
            
            if context:
                metadata.update({
                    "has_memory": bool(context.memory),
                    "memory_items": context.memory.count() if context.memory else 0,
                    "has_intermediate_values": bool(context.intermediate_values) if hasattr(context, 'intermediate_values') else False,
                })
            
            return self.llm_telemetry.generation_span(
                model=self.model,
                operation="pandasai_generation",
                metadata=metadata
            )
        else:
            # Return a no-op context manager
            from contextlib import nullcontext
            return nullcontext({"generation": None, "start_time": time.time()})

    def _call_openai_compatible_with_telemetry(
        self, 
        instruction: BasePrompt, 
        context: AgentState,
        span_data: Dict[str, Any]
    ) -> str:
        """Call OpenAI-compatible API with telemetry tracking"""
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
        
        # Log the request details for MCP visibility
        logger.info(
            "llm_request_started",
            provider=self.provider,
            model=self.model,
            prompt_length=len(instruction.to_string()) if instruction and hasattr(instruction, 'to_string') and instruction.to_string() else 0,
            temperature=data["temperature"],
            max_tokens=data["max_tokens"]
        )
        
        start_time = time.time()
        
        with httpx.Client() as client:
            response = client.post(
                self.api_endpoint,
                headers=headers,
                json=data,
                timeout=300.0  # 5 minutes timeout for complex queries
            )
            response.raise_for_status()
            
        elapsed_time = time.time() - start_time
        result = response.json()
        
        # Extract response content
        response_content = result["choices"][0]["message"]["content"]
        
        # Extract and log token usage if available
        usage = result.get("usage", {})
        if usage and self.llm_telemetry:
            self.llm_telemetry.track_tokens(
                model=self.model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                metadata={
                    "provider": self.provider,
                    "duration_ms": elapsed_time * 1000
                }
            )
        
        # Log response details
        logger.info(
            "llm_response_received",
            provider=self.provider,
            model=self.model,
            response_length=len(response_content) if response_content else 0,
            duration_ms=elapsed_time * 1000,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        )
        
        return response_content

    def _call_ollama_with_telemetry(
        self, 
        instruction: BasePrompt, 
        context: AgentState,
        span_data: Dict[str, Any]
    ) -> str:
        """Call Ollama API with telemetry tracking"""
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
        
        # Log the request details
        logger.info(
            "llm_request_started",
            provider=self.provider,
            model=self.model,
            prompt_length=len(instruction.to_string()) if instruction and hasattr(instruction, 'to_string') and instruction.to_string() else 0,
            temperature=data["options"]["temperature"],
            max_tokens=data["options"]["num_predict"]
        )
        
        start_time = time.time()
        
        with httpx.Client() as client:
            response = client.post(
                self.api_endpoint,
                json=data,
                timeout=300.0  # 5 minutes timeout for complex queries
            )
            response.raise_for_status()
            
        elapsed_time = time.time() - start_time
        result = response.json()
        
        # Extract response content
        response_content = result["message"]["content"]
        
        # Log response details
        logger.info(
            "llm_response_received",
            provider=self.provider,
            model=self.model,
            response_length=len(response_content) if response_content else 0,
            duration_ms=elapsed_time * 1000
        )
        
        return response_content

    def _track_generation_success(
        self, 
        instruction: BasePrompt, 
        response: str,
        span_data: Dict[str, Any]
    ):
        """Track successful generation with telemetry"""
        if self.llm_telemetry:
            # Update the generation with prompt and response
            if span_data.get("generation"):
                span_data["generation"].update(
                    prompt=instruction.to_string(),
                    completion=response,
                    metadata={
                        "success": True,
                        "duration_ms": (time.time() - span_data["start_time"]) * 1000
                    }
                )
            
            # Log structured event for MCP visibility
            logger.info(
                "pandasai_generation_completed",
                event_type="llm_generation",
                provider=self.provider,
                model=self.model,
                prompt_type=instruction.__class__.__name__,
                prompt_preview=instruction.to_string()[:200] + "..." if instruction and hasattr(instruction, 'to_string') and instruction.to_string() and len(instruction.to_string()) > 200 else (instruction.to_string() if instruction and hasattr(instruction, 'to_string') else ""),
                response_preview=response[:200] + "..." if response and len(response) > 200 else (response or ""),
                success=True
            )

    def _track_generation_error(
        self, 
        instruction: BasePrompt, 
        error: Exception,
        span_data: Dict[str, Any]
    ):
        """Track generation error with telemetry"""
        if self.llm_telemetry:
            self.llm_telemetry.track_error(
                model=self.model,
                error=error,
                prompt=instruction.to_string(),
                metadata={
                    "provider": self.provider,
                    "prompt_type": instruction.__class__.__name__
                }
            )
        
        # Log error for MCP visibility
        logger.error(
            "pandasai_generation_failed",
            event_type="llm_error",
            provider=self.provider,
            model=self.model,
            prompt_type=instruction.__class__.__name__,
            error_type=type(error).__name__,
            error_message=str(error)
        )