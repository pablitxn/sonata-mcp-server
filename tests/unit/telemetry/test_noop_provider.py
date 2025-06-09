"""Tests for NoOp telemetry provider."""

import pytest
from datetime import datetime

from telemetry.providers.noop import (
    NoOpSpan,
    NoOpTrace,
    NoOpMetric,
    NoOpLLMTelemetry,
    NoOpTelemetryProvider,
)
from telemetry.interfaces import SpanKind


class TestNoOpSpan:
    """Test NoOpSpan implementation."""
    
    def test_span_methods_do_nothing(self):
        """Test that all span methods execute without error."""
        span = NoOpSpan()
        
        # All methods should do nothing and not raise
        span.set_attribute("key", "value")
        span.set_attributes({"key1": "value1", "key2": "value2"})
        span.add_event("event", {"attr": "value"})
        span.set_status("ok", "All good")
        span.end(datetime.now())
        span.record_exception(Exception("test"))


class TestNoOpTrace:
    """Test NoOpTrace implementation."""
    
    def test_start_span(self):
        """Test starting a span returns NoOpSpan."""
        trace = NoOpTrace()
        span = trace.start_span(
            "test-span",
            kind=SpanKind.SERVER,
            attributes={"key": "value"}
        )
        
        assert isinstance(span, NoOpSpan)
    
    def test_span_context_manager(self):
        """Test span context manager."""
        trace = NoOpTrace()
        
        with trace.span("test-span") as span:
            assert isinstance(span, NoOpSpan)
            span.set_attribute("key", "value")
    
    def test_span_context_manager_with_exception(self):
        """Test span context manager handles exceptions."""
        trace = NoOpTrace()
        
        with pytest.raises(ValueError):
            with trace.span("test-span", record_exception=True) as span:
                raise ValueError("test error")
    
    def test_get_current_context(self):
        """Test getting current context returns empty context."""
        trace = NoOpTrace()
        context = trace.get_current_context()
        
        assert context.trace_id is None
        assert context.span_id is None
        assert context.attributes == {}


class TestNoOpMetric:
    """Test NoOpMetric implementation."""
    
    def test_metric_methods_do_nothing(self):
        """Test that all metric methods execute without error."""
        metric = NoOpMetric()
        
        # All methods should do nothing and not raise
        metric.increment("counter", 1.0, {"tag": "value"})
        metric.gauge("gauge", 42.0, {"tag": "value"})
        metric.histogram("histogram", 100.0, {"tag": "value"}, [50, 100, 200])
        metric.timing("timing", 250.0, {"tag": "value"})
    
    def test_timer_context_manager(self):
        """Test timer context manager."""
        metric = NoOpMetric()
        
        with metric.timer("operation", {"tag": "value"}):
            # Should execute without error
            pass


class TestNoOpLLMTelemetry:
    """Test NoOpLLMTelemetry implementation."""
    
    def test_llm_methods_do_nothing(self):
        """Test that all LLM telemetry methods execute without error."""
        llm = NoOpLLMTelemetry()
        
        # All methods should do nothing and not raise
        llm.track_generation(
            model="gpt-4",
            prompt="test prompt",
            response="test response",
            metadata={"key": "value"}
        )
        
        llm.track_tokens(
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            metadata={"key": "value"}
        )
        
        llm.track_error(
            model="gpt-4",
            error=Exception("test error"),
            prompt="test prompt",
            metadata={"key": "value"}
        )
    
    def test_generation_span_context_manager(self):
        """Test generation span context manager."""
        llm = NoOpLLMTelemetry()
        
        with llm.generation_span("gpt-4", "test", {"key": "value"}) as ctx:
            assert isinstance(ctx, dict)
            ctx["test"] = "value"


class TestNoOpTelemetryProvider:
    """Test NoOpTelemetryProvider implementation."""
    
    def test_provider_initialization(self):
        """Test provider initializes correctly."""
        provider = NoOpTelemetryProvider()
        
        assert provider.get_tracer() is not None
        assert provider.get_metrics() is not None
        assert provider.get_llm_telemetry() is not None
    
    def test_provider_methods_do_nothing(self):
        """Test provider methods execute without error."""
        provider = NoOpTelemetryProvider()
        
        # All methods should do nothing and not raise
        provider.initialize({"key": "value"})
        provider.flush()
        provider.shutdown()
    
    def test_provider_returns_correct_types(self):
        """Test provider returns correct interface implementations."""
        provider = NoOpTelemetryProvider()
        
        assert isinstance(provider.get_tracer(), NoOpTrace)
        assert isinstance(provider.get_metrics(), NoOpMetric)
        assert isinstance(provider.get_llm_telemetry(), NoOpLLMTelemetry)