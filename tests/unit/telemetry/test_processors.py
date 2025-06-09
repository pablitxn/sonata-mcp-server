"""Tests for telemetry processors."""

import pytest
import time
from unittest.mock import MagicMock

from telemetry.processors import (
    TelemetryProcessor,
    PerformanceProcessor,
    add_telemetry_context,
)


class TestTelemetryProcessor:
    """Test TelemetryProcessor for structlog."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.mock_metrics = MagicMock()
        self.mock_tracer = MagicMock()
        self.mock_llm = MagicMock()
        
        self.mock_provider.get_metrics.return_value = self.mock_metrics
        self.mock_provider.get_tracer.return_value = self.mock_tracer
        self.mock_provider.get_llm_telemetry.return_value = self.mock_llm
        
        self.processor = TelemetryProcessor(self.mock_provider)
    
    def test_processor_without_provider(self):
        """Test processor works without provider."""
        processor = TelemetryProcessor(None)
        event_dict = {"event": "test", "level": "info"}
        
        result = processor(None, "info", event_dict)
        assert result == event_dict
    
    def test_extract_telemetry_fields(self):
        """Test extracting telemetry fields from event dict."""
        event_dict = {
            "event": "test",
            "span_name": "test.span",
            "metric_name": "test.metric",
            "metric_value": 42.0,
            "other_field": "value",
        }
        
        fields = self.processor._extract_telemetry_fields(event_dict)
        
        assert fields["span_name"] == "test.span"
        assert fields["metric_name"] == "test.metric"
        assert fields["metric_value"] == 42.0
        assert "span_name" not in event_dict
        assert "metric_name" not in event_dict
        assert "other_field" in event_dict
    
    def test_send_log_metrics(self):
        """Test sending metrics based on log events."""
        event_dict = {"event": "test", "level": "error", "logger": "test.logger"}
        telemetry = {"metric_name": None, "metric_value": None}
        
        self.processor._send_log_metrics("error", event_dict, telemetry)
        
        # Should increment log count and error count
        assert self.mock_metrics.increment.call_count == 2
        self.mock_metrics.increment.assert_any_call(
            "logs.count",
            tags={"level": "error", "logger": "test.logger"}
        )
        self.mock_metrics.increment.assert_any_call(
            "errors.count",
            tags={"type": "log_error"}
        )
    
    def test_send_custom_metrics(self):
        """Test sending custom metrics from log."""
        event_dict = {"event": "test"}
        telemetry = {
            "metric_name": "custom.metric",
            "metric_value": 123.45,
            "metric_tags": {"tag": "value"},
        }
        
        self.processor._send_log_metrics("info", event_dict, telemetry)
        
        self.mock_metrics.gauge.assert_called_once_with(
            "custom.metric",
            123.45,
            {"tag": "value"}
        )
    
    def test_track_llm_generation(self):
        """Test tracking LLM generation events."""
        event_dict = {"event": "llm generation"}
        telemetry = {
            "llm_model": "gpt-4",
            "llm_prompt": "test prompt",
            "llm_response": "test response",
            "llm_tokens": None,
        }
        
        self.processor._track_llm_events(event_dict, telemetry)
        
        self.mock_llm.track_generation.assert_called_once_with(
            model="gpt-4",
            prompt="test prompt",
            response="test response",
            metadata={"log_event": "llm generation"}
        )
    
    def test_track_llm_tokens(self):
        """Test tracking LLM token usage."""
        event_dict = {"event": "token usage"}
        telemetry = {
            "llm_model": "gpt-4",
            "llm_prompt": None,
            "llm_response": None,
            "llm_tokens": {
                "prompt": 100,
                "completion": 200,
                "total": 300,
            },
        }
        
        self.processor._track_llm_events(event_dict, telemetry)
        
        self.mock_llm.track_tokens.assert_called_once_with(
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
        )
    
    def test_processor_handles_exceptions(self):
        """Test processor doesn't fail on exceptions."""
        self.mock_metrics.increment.side_effect = Exception("telemetry error")
        
        event_dict = {"event": "test", "level": "info"}
        result = self.processor(None, "info", event_dict)
        
        # Should return event dict unchanged
        assert result == event_dict


class TestPerformanceProcessor:
    """Test PerformanceProcessor for structlog."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = PerformanceProcessor()
    
    def test_track_operation_duration(self):
        """Test tracking operation duration."""
        # Start operation
        start_event = {
            "event": "start",
            "operation": "test_op",
            "operation_start": True,
        }
        self.processor(None, "info", start_event)
        
        # Small delay
        time.sleep(0.01)
        
        # End operation
        end_event = {
            "event": "end",
            "operation": "test_op",
            "operation_end": True,
        }
        result = self.processor(None, "info", end_event)
        
        assert "duration_ms" in result
        assert result["duration_ms"] > 0
    
    def test_add_memory_usage(self):
        """Test adding memory usage to logs."""
        import sys
        from unittest.mock import Mock
        
        # Create mock psutil module
        mock_psutil = Mock()
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100 MB
        mock_psutil.Process.return_value = mock_process
        
        # Temporarily add to sys.modules
        sys.modules['psutil'] = mock_psutil
        try:
            event_dict = {"event": "test", "include_memory": True}
            result = self.processor(None, "info", event_dict)
            
            assert result["memory_mb"] == 100.0
        finally:
            # Clean up
            if 'psutil' in sys.modules:
                del sys.modules['psutil']
    
    def test_no_memory_without_psutil(self):
        """Test memory tracking works without psutil."""
        import sys
        
        # Ensure psutil is not available
        psutil_backup = sys.modules.get('psutil')
        if 'psutil' in sys.modules:
            del sys.modules['psutil']
        
        try:
            event_dict = {"event": "test", "include_memory": True}
            result = self.processor(None, "info", event_dict)
            
            assert "memory_mb" not in result
        finally:
            # Restore psutil if it was present
            if psutil_backup:
                sys.modules['psutil'] = psutil_backup


class TestAddTelemetryContext:
    """Test add_telemetry_context helper function."""
    
    def test_add_basic_context(self):
        """Test adding basic telemetry context."""
        context = add_telemetry_context(
            span_name="test.span",
            metric_name="test.metric",
            metric_value=42.0,
        )
        
        assert context["span_name"] == "test.span"
        assert context["metric_name"] == "test.metric"
        assert context["metric_value"] == 42.0
    
    def test_add_context_with_kwargs(self):
        """Test adding context with additional kwargs."""
        context = add_telemetry_context(
            span_name="test.span",
            custom_field="custom_value",
            request_id="123",
        )
        
        assert context["span_name"] == "test.span"
        assert context["custom_field"] == "custom_value"
        assert context["request_id"] == "123"
    
    def test_filter_none_values(self):
        """Test that None values are filtered out."""
        context = add_telemetry_context(
            span_name="test.span",
            span_kind=None,
            metric_name=None,
            custom_field="value",
        )
        
        assert "span_name" in context
        assert "span_kind" not in context
        assert "metric_name" not in context
        assert "custom_field" in context