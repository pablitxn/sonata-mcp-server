"""Structlog processors for telemetry integration."""

import time
from typing import Any, Dict, Optional, Tuple

from structlog.types import EventDict, Processor

from .factory import TelemetryFactory
from .interfaces import ITelemetryProvider, SpanKind


class TelemetryProcessor:
    """Structlog processor that sends log events to telemetry."""
    
    def __init__(self, provider: Optional[ITelemetryProvider] = None):
        self.provider = provider or TelemetryFactory.get_instance()
    
    def __call__(
        self, logger: Any, method_name: str, event_dict: EventDict
    ) -> EventDict:
        """Process log event and send to telemetry."""
        if not self.provider:
            return event_dict
        
        try:
            # Extract telemetry-specific fields
            telemetry_fields = self._extract_telemetry_fields(event_dict)
            
            # Send metrics based on log level
            self._send_log_metrics(method_name, event_dict, telemetry_fields)
            
            # Create span events for important operations
            self._create_span_events(event_dict, telemetry_fields)
            
            # Track LLM-specific events
            self._track_llm_events(event_dict, telemetry_fields)
            
        except Exception:
            # Never fail logging due to telemetry errors
            pass
        
        return event_dict
    
    def _extract_telemetry_fields(self, event_dict: EventDict) -> Dict[str, Any]:
        """Extract telemetry-specific fields from event dict."""
        return {
            "span_name": event_dict.pop("span_name", None),
            "span_kind": event_dict.pop("span_kind", None),
            "metric_name": event_dict.pop("metric_name", None),
            "metric_value": event_dict.pop("metric_value", None),
            "metric_tags": event_dict.pop("metric_tags", None),
            "llm_model": event_dict.pop("llm_model", None),
            "llm_prompt": event_dict.pop("llm_prompt", None),
            "llm_response": event_dict.pop("llm_response", None),
            "llm_tokens": event_dict.pop("llm_tokens", None),
        }
    
    def _send_log_metrics(
        self, method_name: str, event_dict: EventDict, telemetry: Dict[str, Any]
    ) -> None:
        """Send metrics based on log events."""
        metrics = self.provider.get_metrics()
        
        # Count logs by level
        level = event_dict.get("level", method_name).lower()
        metrics.increment(
            "logs.count",
            tags={
                "level": level,
                "logger": event_dict.get("logger", "unknown"),
            }
        )
        
        # Track errors
        if level in ("error", "critical"):
            metrics.increment("errors.count", tags={"type": "log_error"})
        
        # Custom metrics from log
        if telemetry["metric_name"] and telemetry["metric_value"] is not None:
            metrics.gauge(
                telemetry["metric_name"],
                telemetry["metric_value"],
                telemetry["metric_tags"],
            )
    
    def _create_span_events(
        self, event_dict: EventDict, telemetry: Dict[str, Any]
    ) -> None:
        """Create span events for traced operations."""
        if not telemetry["span_name"]:
            return
        
        tracer = self.provider.get_tracer()
        span_kind = SpanKind(telemetry["span_kind"] or "internal")
        
        # Add event to current span
        context = tracer.get_current_context()
        if context.span_id:
            # We're inside an active span, add as event
            span = tracer.start_span(
                telemetry["span_name"],
                kind=span_kind,
                attributes={"log_event": event_dict.get("event", "")},
            )
            span.add_event(
                "log",
                attributes={
                    "level": event_dict.get("level", "info"),
                    "message": event_dict.get("event", ""),
                }
            )
            span.end()
    
    def _track_llm_events(
        self, event_dict: EventDict, telemetry: Dict[str, Any]
    ) -> None:
        """Track LLM-specific events."""
        llm_telemetry = self.provider.get_llm_telemetry()
        if not llm_telemetry:
            return
        
        # Track LLM generation
        if telemetry["llm_model"] and telemetry["llm_response"]:
            llm_telemetry.track_generation(
                model=telemetry["llm_model"],
                prompt=telemetry["llm_prompt"] or "",
                response=telemetry["llm_response"],
                metadata={"log_event": event_dict.get("event", "")},
            )
        
        # Track token usage
        if telemetry["llm_tokens"]:
            tokens = telemetry["llm_tokens"]
            if isinstance(tokens, dict) and "total" in tokens:
                llm_telemetry.track_tokens(
                    model=telemetry["llm_model"] or "unknown",
                    prompt_tokens=tokens.get("prompt", 0),
                    completion_tokens=tokens.get("completion", 0),
                    total_tokens=tokens["total"],
                )


class PerformanceProcessor:
    """Structlog processor that adds performance metrics to logs."""
    
    def __init__(self):
        self.start_times: Dict[str, float] = {}
    
    def __call__(
        self, logger: Any, method_name: str, event_dict: EventDict
    ) -> EventDict:
        """Add performance metrics to log events."""
        # Track operation duration
        operation = event_dict.get("operation")
        if operation:
            if event_dict.get("operation_start"):
                self.start_times[operation] = time.time()
            elif event_dict.get("operation_end") and operation in self.start_times:
                duration_ms = (time.time() - self.start_times[operation]) * 1000
                event_dict["duration_ms"] = round(duration_ms, 2)
                del self.start_times[operation]
        
        # Add memory usage if requested
        if event_dict.get("include_memory"):
            try:
                import psutil
                process = psutil.Process()
                event_dict["memory_mb"] = round(process.memory_info().rss / 1024 / 1024, 2)
            except ImportError:
                pass
        
        return event_dict


def add_telemetry_context(
    span_name: Optional[str] = None,
    span_kind: Optional[str] = None,
    metric_name: Optional[str] = None,
    metric_value: Optional[float] = None,
    metric_tags: Optional[Dict[str, str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Helper to add telemetry context to log statements.
    
    Usage:
        logger.info("Processing request", **add_telemetry_context(
            span_name="request.process",
            metric_name="requests.count",
            metric_value=1,
            request_id=request_id
        ))
    """
    context = {
        "span_name": span_name,
        "span_kind": span_kind,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "metric_tags": metric_tags,
    }
    context.update(kwargs)
    return {k: v for k, v in context.items() if v is not None}