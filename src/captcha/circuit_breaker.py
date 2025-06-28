"""Circuit Breaker for resilient captcha service handling.

This module implements the Circuit Breaker pattern to protect against cascading failures
when external captcha solving services become unavailable or unresponsive.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests are blocked
- HALF_OPEN: Testing if service has recovered

This implementation helps maintain system stability and provides graceful degradation
when captcha services experience issues.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

from config.mcp_logger import logger


class CircuitState(Enum):
    """Circuit breaker states.
    
    The circuit breaker transitions between these states based on
    the success or failure of protected calls.
    """
    CLOSED = "closed"  # Normal operation, allows calls
    OPEN = "open"      # Failure detected, blocks calls
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.
    
    These parameters control when the circuit breaker opens, how long it stays open,
    and what conditions are required to close it again.
    """
    failure_threshold: int = 5  # Number of failures to open the circuit
    recovery_timeout: timedelta = timedelta(seconds=60)  # Time before attempting recovery
    success_threshold: int = 3  # Successes needed to close from half-open state
    max_consecutive_failures: int = 3  # Consecutive failures allowed before opening


@dataclass
class CircuitBreakerState:
    """Internal state of the circuit breaker.
    
    Tracks failure counts, success counts, and timing information
    to determine state transitions.
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)


class CircuitBreaker:
    """Circuit breaker for protecting external services.
    
    This class implements the circuit breaker pattern to prevent cascading failures
    when external services (like captcha solvers) become unavailable. It monitors
    call success/failure rates and temporarily blocks calls when failure thresholds
    are exceeded.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize the circuit breaker.
        
        Args:
            name: Name of the protected service (for logging and identification).
            config: Circuit breaker configuration. Uses defaults if not provided.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(circuit_breaker=name)
    
    @property
    def current_state(self) -> CircuitState:
        """Get the current state of the circuit breaker."""
        return self._state.state
    
    def is_open(self) -> bool:
        """Check if the circuit is open (blocking calls)."""
        return self._state.state == CircuitState.OPEN
    
    def is_closed(self) -> bool:
        """Check if the circuit is closed (allowing calls)."""
        return self._state.state == CircuitState.CLOSED
    
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new circuit state.
        
        Handles state-specific cleanup and logging when transitioning between states.
        
        Args:
            new_state: The new circuit state to transition to.
        """
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = datetime.now()
        
        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self._state.failure_count = 0
            self._state.consecutive_failures = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._state.success_count = 0
        
        self.logger.info(
            "circuit_breaker_state_change",
            old_state=old_state.value,
            new_state=new_state.value
        )
    
    async def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt circuit reset.
        
        Returns:
            True if the recovery timeout has elapsed since the last failure.
        """
        if (self._state.last_failure_time and 
            datetime.now() - self._state.last_failure_time >= self.config.recovery_timeout):
            return True
        return False
    
    async def _record_success(self) -> None:
        """Record a successful call.
        
        Updates success counters and potentially transitions the circuit
        from HALF_OPEN to CLOSED if enough successes have occurred.
        """
        async with self._lock:
            self._state.consecutive_failures = 0
            
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def _record_failure(self) -> None:
        """Record a failed call.
        
        Updates failure counters and potentially transitions the circuit
        to OPEN state if failure thresholds are exceeded.
        """
        async with self._lock:
            self._state.failure_count += 1
            self._state.consecutive_failures += 1
            self._state.last_failure_time = datetime.now()
            
            # Check if we should open the circuit
            if self._state.state == CircuitState.CLOSED:
                if (self._state.failure_count >= self.config.failure_threshold or
                    self._state.consecutive_failures >= self.config.max_consecutive_failures):
                    await self._transition_to(CircuitState.OPEN)
            elif self._state.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                await self._transition_to(CircuitState.OPEN)
    
    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function protected by the circuit breaker.
        
        This method wraps the provided function call with circuit breaker logic.
        If the circuit is open, it will either block the call or transition to
        half-open state if the recovery timeout has elapsed.
        
        Args:
            func: The async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            The result of the function call if successful.
            
        Raises:
            CircuitBreakerOpen: If the circuit is open and not ready for reset.
            Any exception raised by the wrapped function.
        """
        # Check circuit state before attempting call
        async with self._lock:
            if self._state.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is open"
                    )
        
        # Attempt the call
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the circuit breaker.
        
        Useful for monitoring and debugging circuit breaker behavior.
        
        Returns:
            Dictionary containing current state information including:
            - name: Circuit breaker name
            - state: Current state (closed/open/half_open)
            - failure_count: Total failures since last reset
            - success_count: Successes in half-open state
            - consecutive_failures: Current consecutive failure streak
            - last_failure_time: ISO timestamp of last failure
            - last_state_change: ISO timestamp of last state transition
        """
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "consecutive_failures": self._state.consecutive_failures,
            "last_failure_time": self._state.last_failure_time.isoformat() if self._state.last_failure_time else None,
            "last_state_change": self._state.last_state_change.isoformat()
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when the circuit breaker is open.
    
    This exception is raised when a call is attempted through an open circuit breaker,
    indicating that the protected service is currently unavailable.
    """
    pass