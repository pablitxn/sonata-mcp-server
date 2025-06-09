"""Context managers and decorators for telemetry integration."""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from src.config.telemetry_logger import logger, get_telemetry, add_telemetry_context
from .interfaces import SpanKind


F = TypeVar('F', bound=Callable[..., Any])


@contextmanager
def traced_operation(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
    log_start: bool = True,
    log_end: bool = True,
):
    """Context manager for traced operations with logging.
    
    Usage:
        with traced_operation("database.query", attributes={"query": sql}):
            result = db.execute(sql)
    """
    telemetry = get_telemetry()
    span = None
    start_time = time.time()
    
    # Log operation start
    if log_start:
        logger.info(
            f"{name}: started",
            **add_telemetry_context(
                span_name=name,
                span_kind=kind.value,
                operation=name,
                operation_start=True,
                **(attributes or {})
            )
        )
    
    # Start telemetry span if available
    if telemetry:
        tracer = telemetry.get_tracer()
        span = tracer.start_span(name, kind=kind, attributes=attributes)
    
    try:
        yield span
        
        # Log successful completion
        if log_end:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"{name}: completed",
                **add_telemetry_context(
                    span_name=name,
                    operation=name,
                    operation_end=True,
                    duration_ms=duration_ms,
                    metric_name=f"{name}.duration",
                    metric_value=duration_ms,
                )
            )
    except Exception as e:
        # Log error
        logger.error(
            f"{name}: failed",
            **add_telemetry_context(
                span_name=name,
                operation=name,
                operation_end=True,
                error=str(e),
                error_type=type(e).__name__,
            )
        )
        
        # Record exception in span
        if span and record_exception:
            span.record_exception(e)
            span.set_status("error", str(e))
        
        raise
    finally:
        if span:
            span.end()


def trace(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    log_args: bool = False,
    log_result: bool = False,
):
    """Decorator for tracing functions with telemetry and logging.
    
    Usage:
        @trace("api.endpoint")
        async def handle_request(request):
            return {"status": "ok"}
    """
    def decorator(func: F) -> F:
        operation_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            attrs = attributes or {}
            if log_args:
                attrs["args"] = str(args)
                attrs["kwargs"] = str(kwargs)
            
            with traced_operation(
                operation_name,
                kind=kind,
                attributes=attrs,
            ) as span:
                result = await func(*args, **kwargs)
                
                if log_result and span:
                    span.set_attribute("result", str(result))
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            attrs = attributes or {}
            if log_args:
                attrs["args"] = str(args)
                attrs["kwargs"] = str(kwargs)
            
            with traced_operation(
                operation_name,
                kind=kind,
                attributes=attrs,
            ) as span:
                result = func(*args, **kwargs)
                
                if log_result and span:
                    span.set_attribute("result", str(result))
                
                return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@contextmanager
def timed_operation(
    metric_name: str,
    tags: Optional[Dict[str, str]] = None,
    log_slow_threshold_ms: Optional[float] = None,
):
    """Context manager for timing operations and sending metrics.
    
    Usage:
        with timed_operation("database.query.time", tags={"table": "users"}):
            results = db.query("SELECT * FROM users")
    """
    telemetry = get_telemetry()
    start_time = time.time()
    
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        
        # Send metric
        if telemetry:
            metrics = telemetry.get_metrics()
            metrics.timing(metric_name, duration_ms, tags)
        
        # Log if slow
        if log_slow_threshold_ms and duration_ms > log_slow_threshold_ms:
            logger.warning(
                f"Slow operation: {metric_name}",
                **add_telemetry_context(
                    metric_name=metric_name,
                    metric_value=duration_ms,
                    metric_tags=tags,
                    duration_ms=duration_ms,
                    slow_operation=True,
                )
            )


@contextmanager
def llm_generation(
    model: str,
    operation: str = "generation",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Context manager for tracking LLM generations.
    
    Usage:
        with llm_generation("gpt-4", metadata={"temperature": 0.7}) as ctx:
            response = await llm.generate(prompt)
            ctx["prompt"] = prompt
            ctx["response"] = response
            ctx["tokens"] = {"prompt": 100, "completion": 200, "total": 300}
    """
    telemetry = get_telemetry()
    llm_telemetry = telemetry.get_llm_telemetry() if telemetry else None
    
    context = {
        "model": model,
        "operation": operation,
        "metadata": metadata or {},
        "prompt": None,
        "response": None,
        "tokens": None,
        "error": None,
    }
    
    # Log generation start
    logger.info(
        f"llm.{operation}: started",
        **add_telemetry_context(
            llm_model=model,
            operation=operation,
            **(metadata or {})
        )
    )
    
    start_time = time.time()
    
    try:
        yield context
        
        # Track successful generation
        if llm_telemetry and context["response"]:
            llm_telemetry.track_generation(
                model=model,
                prompt=context["prompt"] or "",
                response=context["response"],
                metadata={
                    **context["metadata"],
                    "operation": operation,
                    "duration_ms": (time.time() - start_time) * 1000,
                }
            )
        
        # Track token usage
        if llm_telemetry and context["tokens"]:
            tokens = context["tokens"]
            llm_telemetry.track_tokens(
                model=model,
                prompt_tokens=tokens.get("prompt", 0),
                completion_tokens=tokens.get("completion", 0),
                total_tokens=tokens.get("total", 0),
                metadata=context["metadata"],
            )
        
        # Log completion
        logger.info(
            f"llm.{operation}: completed",
            **add_telemetry_context(
                llm_model=model,
                llm_response=context["response"][:100] if context["response"] else None,
                llm_tokens=context["tokens"],
                duration_ms=(time.time() - start_time) * 1000,
            )
        )
        
    except Exception as e:
        context["error"] = e
        
        # Track error
        if llm_telemetry:
            llm_telemetry.track_error(
                model=model,
                error=e,
                prompt=context["prompt"],
                metadata=context["metadata"],
            )
        
        # Log error
        logger.error(
            f"llm.{operation}: failed",
            **add_telemetry_context(
                llm_model=model,
                error=str(e),
                error_type=type(e).__name__,
            )
        )
        
        raise


# Fix import
import asyncio