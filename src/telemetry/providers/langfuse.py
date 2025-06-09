"""Langfuse telemetry provider for LLM observability."""

import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, ContextManager
from uuid import uuid4

from ..interfaces import (
    ILLMTelemetry,
    IMetric,
    ISpan,
    ITelemetryProvider,
    ITrace,
    SpanKind,
    TelemetryContext,
)


class LangfuseSpan(ISpan):
    """Langfuse-compatible span implementation."""
    
    def __init__(self, trace_client: Any, name: str, metadata: Optional[Dict[str, Any]] = None):
        self.trace_client = trace_client
        self.span = None
        self.name = name
        self.start_time = time.time()
        self.attributes = {}
        self.metadata = metadata or {}
        
        if hasattr(trace_client, 'span'):
            self.span = trace_client.span(
                name=name,
                metadata=self.metadata,
            )
    
    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value
        if self.span:
            self.span.update(metadata={**self.metadata, key: value})
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        self.attributes.update(attributes)
        if self.span:
            self.span.update(metadata={**self.metadata, **attributes})
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        if self.span and hasattr(self.span, 'event'):
            self.span.event(
                name=name,
                metadata=attributes or {},
            )
    
    def set_status(self, status: str, description: Optional[str] = None) -> None:
        if self.span:
            self.span.update(
                metadata={
                    **self.metadata,
                    "status": status,
                    "status_description": description,
                }
            )
    
    def end(self, end_time: Optional[datetime] = None) -> None:
        if self.span:
            self.span.end()
    
    def record_exception(self, exception: Exception) -> None:
        if self.span:
            self.span.update(
                metadata={
                    **self.metadata,
                    "error": True,
                    "error_type": type(exception).__name__,
                    "error_message": str(exception),
                }
            )


class LangfuseTrace(ITrace):
    """Langfuse trace implementation."""
    
    def __init__(self, langfuse_client: Any):
        self.client = langfuse_client
        self.active_trace = None
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[TelemetryContext] = None,
    ) -> ISpan:
        metadata = {
            "kind": kind.value,
            **(attributes or {}),
        }
        
        if not self.active_trace:
            self.active_trace = self.client.trace(
                name=name,
                metadata=metadata,
            )
            return LangfuseSpan(self.active_trace, name, metadata)
        else:
            return LangfuseSpan(self.active_trace, name, metadata)
    
    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True,
    ) -> ContextManager[ISpan]:
        span = self.start_span(name, kind, attributes)
        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
            raise
        finally:
            span.end()
    
    def get_current_context(self) -> TelemetryContext:
        if self.active_trace:
            return TelemetryContext(
                trace_id=getattr(self.active_trace, 'trace_id', None),
            )
        return TelemetryContext()


class LangfuseMetric(IMetric):
    """Langfuse metric implementation using events."""
    
    def __init__(self, langfuse_client: Any):
        self.client = langfuse_client
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.client.event(
            name=f"metric.{name}",
            metadata={
                "type": "counter",
                "value": value,
                "tags": tags or {},
            }
        )
    
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.client.event(
            name=f"metric.{name}",
            metadata={
                "type": "gauge",
                "value": value,
                "tags": tags or {},
            }
        )
    
    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> None:
        self.client.event(
            name=f"metric.{name}",
            metadata={
                "type": "histogram",
                "value": value,
                "tags": tags or {},
                "buckets": buckets,
            }
        )
    
    def timing(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.client.event(
            name=f"metric.{name}",
            metadata={
                "type": "timing",
                "value": value,
                "unit": "ms",
                "tags": tags or {},
            }
        )
    
    @contextmanager
    def timer(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> ContextManager[None]:
        start_time = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.timing(name, elapsed_ms, tags)


class LangfuseLLMTelemetry(ILLMTelemetry):
    """Langfuse-specific LLM telemetry implementation."""
    
    def __init__(self, langfuse_client: Any):
        self.client = langfuse_client
    
    def track_generation(
        self,
        model: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        generation = self.client.generation(
            name="llm_generation",
            model=model,
            prompt=prompt,
            completion=response,
            metadata=metadata or {},
        )
        generation.end()
    
    def track_tokens(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.client.generation(
            name="token_usage",
            model=model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            metadata=metadata or {},
        ).end()
    
    def track_error(
        self,
        model: str,
        error: Exception,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_metadata = {
            "error": True,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(metadata or {}),
        }
        
        generation = self.client.generation(
            name="llm_error",
            model=model,
            prompt=prompt,
            metadata=error_metadata,
        )
        generation.end()
    
    @contextmanager
    def generation_span(
        self,
        model: str,
        operation: str = "generation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextManager[Dict[str, Any]]:
        generation_data = {
            "generation": None,
            "start_time": time.time(),
        }
        
        generation = self.client.generation(
            name=operation,
            model=model,
            metadata=metadata or {},
        )
        generation_data["generation"] = generation
        
        try:
            yield generation_data
        except Exception as e:
            generation.update(
                metadata={
                    "error": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            raise
        finally:
            generation.end()


class LangfuseTelemetryProvider(ITelemetryProvider):
    """Langfuse telemetry provider for LLM observability."""
    
    def __init__(self):
        self.client = None
        self._trace = None
        self._metrics = None
        self._llm_telemetry = None
        self.config = {}
    
    def get_tracer(self) -> ITrace:
        if not self._trace:
            raise RuntimeError("Telemetry provider not initialized")
        return self._trace
    
    def get_metrics(self) -> IMetric:
        if not self._metrics:
            raise RuntimeError("Telemetry provider not initialized")
        return self._metrics
    
    def get_llm_telemetry(self) -> Optional[ILLMTelemetry]:
        return self._llm_telemetry
    
    def initialize(self, config: Dict[str, Any]) -> None:
        try:
            from langfuse import Langfuse
        except ImportError:
            raise RuntimeError(
                "Langfuse package not installed. Install with: pip install langfuse"
            )
        
        self.config = config
        
        # Initialize Langfuse client
        self.client = Langfuse(
            public_key=config.get("langfuse_public_key"),
            secret_key=config.get("langfuse_secret_key"),
            host=config.get("langfuse_host", "https://cloud.langfuse.com"),
            debug=config.get("debug", False),
        )
        
        # Initialize components
        self._trace = LangfuseTrace(self.client)
        self._metrics = LangfuseMetric(self.client)
        self._llm_telemetry = LangfuseLLMTelemetry(self.client)
    
    def shutdown(self) -> None:
        if self.client:
            self.flush()
    
    def flush(self) -> None:
        if self.client and hasattr(self.client, 'flush'):
            self.client.flush()