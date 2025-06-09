"""Tests for telemetry interfaces."""

import pytest
from datetime import datetime

from telemetry.interfaces import (
    SpanKind,
    MetricType,
    TelemetryContext,
)


class TestEnums:
    """Test telemetry enumerations."""
    
    def test_span_kind_values(self):
        """Test SpanKind enum values."""
        assert SpanKind.INTERNAL.value == "internal"
        assert SpanKind.SERVER.value == "server"
        assert SpanKind.CLIENT.value == "client"
        assert SpanKind.PRODUCER.value == "producer"
        assert SpanKind.CONSUMER.value == "consumer"
    
    def test_metric_type_values(self):
        """Test MetricType enum values."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"


class TestTelemetryContext:
    """Test TelemetryContext dataclass."""
    
    def test_default_context(self):
        """Test default TelemetryContext creation."""
        context = TelemetryContext()
        
        assert context.trace_id is None
        assert context.span_id is None
        assert context.user_id is None
        assert context.session_id is None
        assert context.attributes == {}
    
    def test_context_with_values(self):
        """Test TelemetryContext with custom values."""
        context = TelemetryContext(
            trace_id="trace-123",
            span_id="span-456",
            user_id="user-789",
            session_id="session-abc",
            attributes={"key": "value"}
        )
        
        assert context.trace_id == "trace-123"
        assert context.span_id == "span-456"
        assert context.user_id == "user-789"
        assert context.session_id == "session-abc"
        assert context.attributes == {"key": "value"}