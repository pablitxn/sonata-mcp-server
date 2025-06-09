"""No-operation telemetry provider for testing and development."""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, ContextManager

from ..interfaces import (
    ILLMTelemetry,
    IMetric,
    ISpan,
    ITelemetryProvider,
    ITrace,
    SpanKind,
    TelemetryContext,
)


class NoOpSpan(ISpan):
    """No-op implementation of ISpan."""
    
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass
    
    def set_status(self, status: str, description: Optional[str] = None) -> None:
        pass
    
    def end(self, end_time: Optional[datetime] = None) -> None:
        pass
    
    def record_exception(self, exception: Exception) -> None:
        pass


class NoOpTrace(ITrace):
    """No-op implementation of ITrace."""
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[TelemetryContext] = None,
    ) -> ISpan:
        return NoOpSpan()
    
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
        return TelemetryContext()


class NoOpMetric(IMetric):
    """No-op implementation of IMetric."""
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        pass
    
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        pass
    
    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> None:
        pass
    
    def timing(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        pass
    
    @contextmanager
    def timer(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> ContextManager[None]:
        yield


class NoOpLLMTelemetry(ILLMTelemetry):
    """No-op implementation of ILLMTelemetry."""
    
    def track_generation(
        self,
        model: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass
    
    def track_tokens(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass
    
    def track_error(
        self,
        model: str,
        error: Exception,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass
    
    @contextmanager
    def generation_span(
        self,
        model: str,
        operation: str = "generation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextManager[Dict[str, Any]]:
        yield {}


class NoOpTelemetryProvider(ITelemetryProvider):
    """No-operation telemetry provider that does nothing."""
    
    def __init__(self):
        self._trace = NoOpTrace()
        self._metrics = NoOpMetric()
        self._llm_telemetry = NoOpLLMTelemetry()
    
    def get_tracer(self) -> ITrace:
        return self._trace
    
    def get_metrics(self) -> IMetric:
        return self._metrics
    
    def get_llm_telemetry(self) -> Optional[ILLMTelemetry]:
        return self._llm_telemetry
    
    def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    def shutdown(self) -> None:
        pass
    
    def flush(self) -> None:
        pass