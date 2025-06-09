"""Telemetry interfaces and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, ContextManager
from contextlib import contextmanager


class SpanKind(Enum):
    """Types of spans in distributed tracing."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class TelemetryContext:
    """Context information for telemetry operations."""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


class ISpan(ABC):
    """Interface for a trace span."""
    
    @abstractmethod
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        pass
    
    @abstractmethod
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple attributes on the span."""
        pass
    
    @abstractmethod
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        pass
    
    @abstractmethod
    def set_status(self, status: str, description: Optional[str] = None) -> None:
        """Set the span status."""
        pass
    
    @abstractmethod
    def end(self, end_time: Optional[datetime] = None) -> None:
        """End the span."""
        pass
    
    @abstractmethod
    def record_exception(self, exception: Exception) -> None:
        """Record an exception in the span."""
        pass


class ITrace(ABC):
    """Interface for distributed tracing."""
    
    @abstractmethod
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[TelemetryContext] = None,
    ) -> ISpan:
        """Start a new span."""
        pass
    
    @abstractmethod
    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True,
    ) -> ContextManager[ISpan]:
        """Create a span context manager."""
        pass
    
    @abstractmethod
    def get_current_context(self) -> TelemetryContext:
        """Get the current telemetry context."""
        pass


class IMetric(ABC):
    """Interface for metrics collection."""
    
    @abstractmethod
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric."""
        pass
    
    @abstractmethod
    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> None:
        """Record a histogram metric."""
        pass
    
    @abstractmethod
    def timing(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a timing metric (in milliseconds)."""
        pass
    
    @abstractmethod
    @contextmanager
    def timer(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> ContextManager[None]:
        """Context manager for timing operations."""
        pass


class ILLMTelemetry(ABC):
    """Interface for LLM-specific telemetry."""
    
    @abstractmethod
    def track_generation(
        self,
        model: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an LLM generation event."""
        pass
    
    @abstractmethod
    def track_tokens(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track token usage."""
        pass
    
    @abstractmethod
    def track_error(
        self,
        model: str,
        error: Exception,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an LLM error."""
        pass
    
    @abstractmethod
    @contextmanager
    def generation_span(
        self,
        model: str,
        operation: str = "generation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextManager[Dict[str, Any]]:
        """Context manager for tracking LLM generations."""
        pass


class ITelemetryProvider(ABC):
    """Main interface for telemetry providers."""
    
    @abstractmethod
    def get_tracer(self) -> ITrace:
        """Get the trace interface."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> IMetric:
        """Get the metrics interface."""
        pass
    
    @abstractmethod
    def get_llm_telemetry(self) -> Optional[ILLMTelemetry]:
        """Get the LLM telemetry interface if available."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the telemetry provider with configuration."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the telemetry provider and flush any pending data."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Force flush any pending telemetry data."""
        pass