"""Tests for telemetry context managers and decorators."""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch

from telemetry.context import (
    traced_operation,
    trace,
    timed_operation,
    llm_generation,
)
from telemetry.interfaces import SpanKind


class TestTracedOperation:
    """Test traced_operation context manager."""
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_successful_operation(self, mock_logger, mock_get_telemetry):
        """Test tracing successful operation."""
        mock_provider = MagicMock()
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        mock_get_telemetry.return_value = mock_provider
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer.start_span.return_value = mock_span
        
        with traced_operation(
            "test.operation",
            kind=SpanKind.SERVER,
            attributes={"key": "value"}
        ) as span:
            assert span == mock_span
        
        # Verify span was started and ended
        mock_tracer.start_span.assert_called_once_with(
            "test.operation",
            kind=SpanKind.SERVER,
            attributes={"key": "value"}
        )
        mock_span.end.assert_called_once()
        
        # Verify logging
        assert mock_logger.info.call_count == 2
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_operation_with_exception(self, mock_logger, mock_get_telemetry):
        """Test tracing operation that raises exception."""
        mock_provider = MagicMock()
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        mock_get_telemetry.return_value = mock_provider
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer.start_span.return_value = mock_span
        
        with pytest.raises(ValueError):
            with traced_operation("test.operation"):
                raise ValueError("test error")
        
        # Verify exception was recorded
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once_with("error", "test error")
        mock_span.end.assert_called_once()
        
        # Verify error logging
        mock_logger.error.assert_called_once()
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_operation_without_telemetry(self, mock_logger, mock_get_telemetry):
        """Test operation works without telemetry provider."""
        mock_get_telemetry.return_value = None
        
        with traced_operation("test.operation") as span:
            assert span is None
        
        # Should still log
        assert mock_logger.info.call_count == 2


class TestTraceDecorator:
    """Test trace decorator."""
    
    @patch("telemetry.context.traced_operation")
    def test_sync_function(self, mock_traced_operation):
        """Test decorating synchronous function."""
        mock_context = MagicMock()
        mock_span = MagicMock()
        mock_context.__enter__.return_value = mock_span
        mock_context.__exit__.return_value = None
        mock_traced_operation.return_value = mock_context
        
        @trace("test.function")
        def test_func(a, b):
            return a + b
        
        result = test_func(1, 2)
        assert result == 3
        
        mock_traced_operation.assert_called_once_with(
            "test.function",
            kind=SpanKind.INTERNAL,
            attributes={},
        )
    
    @patch("telemetry.context.traced_operation")
    @pytest.mark.asyncio
    async def test_async_function(self, mock_traced_operation):
        """Test decorating asynchronous function."""
        mock_context = MagicMock()
        mock_span = MagicMock()
        mock_context.__enter__.return_value = mock_span
        mock_context.__exit__.return_value = None
        mock_traced_operation.return_value = mock_context
        
        @trace("test.async_function", log_args=True)
        async def test_func(a, b):
            await asyncio.sleep(0.001)
            return a + b
        
        result = await test_func(1, 2)
        assert result == 3
        
        # Check that args were logged
        call_args = mock_traced_operation.call_args[1]["attributes"]
        assert "args" in call_args
        assert "kwargs" in call_args
    
    def test_decorator_without_name(self):
        """Test decorator generates name from function."""
        with patch("telemetry.context.traced_operation") as mock_traced_operation:
            mock_context = MagicMock()
            mock_context.__enter__.return_value = MagicMock()
            mock_context.__exit__.return_value = None
            mock_traced_operation.return_value = mock_context
            
            @trace()
            def test_func():
                return "result"
            
            test_func()
            
            # Should use module.function name
            operation_name = mock_traced_operation.call_args[0][0]
            assert "test_func" in operation_name


class TestTimedOperation:
    """Test timed_operation context manager."""
    
    @patch("telemetry.context.get_telemetry")
    def test_timing_operation(self, mock_get_telemetry):
        """Test timing an operation."""
        mock_provider = MagicMock()
        mock_metrics = MagicMock()
        
        mock_get_telemetry.return_value = mock_provider
        mock_provider.get_metrics.return_value = mock_metrics
        
        with timed_operation("test.timing", tags={"env": "test"}):
            time.sleep(0.01)
        
        # Verify timing was recorded
        mock_metrics.timing.assert_called_once()
        call_args = mock_metrics.timing.call_args
        assert call_args[0][0] == "test.timing"
        assert call_args[0][1] > 0  # Duration should be positive
        assert call_args[0][2] == {"env": "test"}  # tags is positional arg
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_slow_operation_logging(self, mock_logger, mock_get_telemetry):
        """Test logging slow operations."""
        mock_get_telemetry.return_value = None
        
        with timed_operation(
            "test.slow",
            log_slow_threshold_ms=1
        ):
            time.sleep(0.01)
        
        # Should log warning for slow operation
        mock_logger.warning.assert_called_once()


class TestLLMGeneration:
    """Test llm_generation context manager."""
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_successful_generation(self, mock_logger, mock_get_telemetry):
        """Test tracking successful LLM generation."""
        mock_provider = MagicMock()
        mock_llm = MagicMock()
        
        mock_get_telemetry.return_value = mock_provider
        mock_provider.get_llm_telemetry.return_value = mock_llm
        
        with llm_generation(
            "gpt-4",
            operation="chat",
            metadata={"temperature": 0.7}
        ) as ctx:
            ctx["prompt"] = "test prompt"
            ctx["response"] = "test response"
            ctx["tokens"] = {
                "prompt": 10,
                "completion": 20,
                "total": 30,
            }
        
        # Verify generation was tracked
        mock_llm.track_generation.assert_called_once()
        mock_llm.track_tokens.assert_called_once()
        
        # Verify logging
        assert mock_logger.info.call_count == 2
    
    @patch("telemetry.context.get_telemetry")
    @patch("telemetry.context.logger")
    def test_generation_with_error(self, mock_logger, mock_get_telemetry):
        """Test tracking LLM generation error."""
        mock_provider = MagicMock()
        mock_llm = MagicMock()
        
        mock_get_telemetry.return_value = mock_provider
        mock_provider.get_llm_telemetry.return_value = mock_llm
        
        with pytest.raises(ValueError):
            with llm_generation("gpt-4") as ctx:
                ctx["prompt"] = "test prompt"
                raise ValueError("API error")
        
        # Verify error was tracked
        mock_llm.track_error.assert_called_once()
        error_call = mock_llm.track_error.call_args
        assert error_call[1]["model"] == "gpt-4"
        assert isinstance(error_call[1]["error"], ValueError)
        
        # Verify error logging
        mock_logger.error.assert_called_once()