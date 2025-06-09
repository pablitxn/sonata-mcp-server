"""Examples of telemetry integration with existing code."""

from typing import Any, Dict

from config.telemetry_logger import logger, add_telemetry_context
from telemetry import traced_operation, trace, timed_operation, llm_generation, SpanKind


# Example 1: Basic tool with telemetry
@trace("tool.add", kind=SpanKind.SERVER)
def add_with_telemetry(a: int, b: int) -> int:
    """Add two numbers with telemetry tracking."""
    result = a + b
    
    # Log with metric
    logger.info(
        "tool.add: calculated sum",
        **add_telemetry_context(
            metric_name="tools.add.result",
            metric_value=result,
            metric_tags={"operation": "addition"},
            a=a,
            b=b,
            result=result,
        )
    )
    
    return result


# Example 2: Browser operation with timing
async def navigate_with_telemetry(browser, url: str):
    """Navigate to URL with performance tracking."""
    with traced_operation(
        "browser.navigate",
        kind=SpanKind.CLIENT,
        attributes={"url": url, "browser": "playwright"}
    ):
        with timed_operation(
            "browser.page_load_time",
            tags={"browser": "playwright"},
            log_slow_threshold_ms=5000,
        ):
            await browser.goto(url)
            logger.info(
                "browser.navigate: page loaded",
                url=url,
                title=await browser.title(),
            )


# Example 3: AFIP connector with detailed telemetry
class AFIPConnectorWithTelemetry:
    """Example of AFIP connector with integrated telemetry."""
    
    @trace("afip.login", kind=SpanKind.CLIENT, log_args=True)
    async def login(self, cuit: str, password: str) -> Dict[str, Any]:
        """Login to AFIP with telemetry."""
        # Mask sensitive data in logs
        masked_cuit = f"{cuit[:2]}****{cuit[-2:]}" if len(cuit) > 4 else "****"
        
        logger.info(
            "afip.login: starting authentication",
            **add_telemetry_context(
                span_name="afip.login",
                cuit=masked_cuit,
                metric_name="afip.login.attempts",
                metric_value=1,
            )
        )
        
        try:
            # Simulate login process
            with timed_operation("afip.login.duration", tags={"service": "afip"}):
                # Actual login logic here
                session = {"token": "fake-token", "user": masked_cuit}
            
            logger.info(
                "afip.login: authentication successful",
                cuit=masked_cuit,
                session_created=True,
            )
            
            return session
            
        except Exception as e:
            logger.error(
                "afip.login: authentication failed",
                **add_telemetry_context(
                    metric_name="afip.login.failures",
                    metric_value=1,
                    metric_tags={"error_type": type(e).__name__},
                    cuit=masked_cuit,
                    error=str(e),
                )
            )
            raise


# Example 4: LLM integration with Langfuse
async def process_with_llm(prompt: str, model: str = "gpt-4"):
    """Process prompt with LLM and track with telemetry."""
    with llm_generation(
        model=model,
        operation="text_processing",
        metadata={
            "temperature": 0.7,
            "max_tokens": 1000,
            "use_case": "code_generation",
        }
    ) as ctx:
        # Store prompt for telemetry
        ctx["prompt"] = prompt
        
        try:
            # Simulate LLM call
            response = f"Generated response for: {prompt[:50]}..."
            tokens = {
                "prompt": len(prompt.split()),
                "completion": len(response.split()),
                "total": len(prompt.split()) + len(response.split()),
            }
            
            # Store response and tokens for telemetry
            ctx["response"] = response
            ctx["tokens"] = tokens
            
            return response
            
        except Exception as e:
            # Error is automatically tracked by context manager
            raise


# Example 5: Captcha solving with circuit breaker telemetry
class CaptchaSolverWithTelemetry:
    """Captcha solver with telemetry for success rates."""
    
    @trace("captcha.solve", kind=SpanKind.CLIENT)
    async def solve_captcha(self, image_data: bytes, provider: str = "2captcha"):
        """Solve captcha with telemetry tracking."""
        with traced_operation(
            f"captcha.{provider}.solve",
            attributes={
                "provider": provider,
                "image_size": len(image_data),
            }
        ) as span:
            try:
                # Simulate captcha solving
                solution = "fake-solution"
                
                # Track success
                logger.info(
                    f"captcha.{provider}: solved successfully",
                    **add_telemetry_context(
                        metric_name="captcha.success_rate",
                        metric_value=1,
                        metric_tags={"provider": provider},
                        solution_length=len(solution),
                    )
                )
                
                return solution
                
            except Exception as e:
                # Track failure
                logger.error(
                    f"captcha.{provider}: solving failed",
                    **add_telemetry_context(
                        metric_name="captcha.failure_rate", 
                        metric_value=1,
                        metric_tags={
                            "provider": provider,
                            "error_type": type(e).__name__,
                        },
                    )
                )
                raise


# Example 6: Session storage with performance tracking
class SessionStorageWithTelemetry:
    """Session storage with telemetry for cache performance."""
    
    @timed_operation("session.save.duration")
    async def save_session(self, session_id: str, data: Dict[str, Any]):
        """Save session with timing."""
        logger.info(
            "session.save: storing session",
            session_id=session_id,
            data_size=len(str(data)),
        )
        # Actual save logic here
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session with cache metrics."""
        with traced_operation("session.get", attributes={"session_id": session_id}):
            # Check cache
            cache_hit = True  # Simulate cache check
            
            logger.info(
                "session.get: retrieving session",
                **add_telemetry_context(
                    metric_name="session.cache_hit_rate",
                    metric_value=1 if cache_hit else 0,
                    session_id=session_id,
                    cache_hit=cache_hit,
                )
            )
            
            # Return session data
            return {"data": "session-data"}