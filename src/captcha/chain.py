"""Chain of Responsibility pattern for captcha resolution.

This module implements a flexible and resilient captcha solving system using the Chain of Responsibility pattern.
Each solver in the chain is protected by a circuit breaker to prevent cascading failures.

Key features:
- Multiple captcha solvers can be chained together
- Automatic fallback to the next solver if one fails
- Circuit breaker protection for each solver
- Comprehensive logging and status monitoring
"""

from typing import Any, Dict, List, Optional

from browser.interfaces import IPage
from config.mcp_logger import logger
from telemetry.factory import get_telemetry_provider
from telemetry.interfaces import ITelemetryProvider
from .interfaces import ICaptchaSolver
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen


class CaptchaSolverHandler:
    """Handler for a captcha solver with circuit breaker protection.
    
    This class wraps a captcha solver with circuit breaker functionality,
    allowing it to participate in a chain of responsibility pattern.
    If the solver fails or is unavailable, the request is passed to the next handler.
    """
    
    _telemetry: ITelemetryProvider = get_telemetry_provider()
    
    def __init__(
        self,
        solver: ICaptchaSolver,
        circuit_breaker: Optional[CircuitBreaker] = None,
        next_handler: Optional['CaptchaSolverHandler'] = None
    ):
        """Initialize the handler.
        
        Args:
            solver: The captcha solver implementation.
            circuit_breaker: Optional circuit breaker instance. If not provided,
                           a new one will be created with default configuration.
            next_handler: The next handler in the chain (optional).
        """
        self.solver = solver
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name=solver.__class__.__name__,
            config=CircuitBreakerConfig()
        )
        self.next_handler = next_handler
        self.logger = logger.bind(solver=solver.__class__.__name__)
    
    async def handle(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Handle the captcha resolution request.
        
        This method attempts to solve the captcha using the wrapped solver.
        If the solver cannot handle the captcha type or fails, the request
        is passed to the next handler in the chain.
        
        Args:
            page: The page interface containing the captcha.
            captcha_info: Dictionary with captcha details (type, sitekey, etc.).
            
        Returns:
            The captcha solution string if successful, None otherwise.
        """
        captcha_type = captcha_info.get("type", "unknown")
        
        # Start telemetry span for this solver attempt
        with self._telemetry.trace("captcha_solve_attempt") as trace:
            trace.add_metadata({
                "solver": self.solver.__class__.__name__,
                "captcha_type": captcha_type,
                "circuit_breaker_state": self.circuit_breaker.current_state.value if self.circuit_breaker else "no_circuit_breaker"
            })
            
            # Check if this solver can handle the captcha type
            if not self.solver.can_handle(captcha_type):
                self.logger.debug("captcha_handler.handle: solver cannot handle captcha type", 
                                captcha_type=captcha_type,
                                solver=self.solver.__class__.__name__)
                if self.next_handler:
                    self.logger.debug("captcha_handler.handle: passing to next handler",
                                    next_solver=self.next_handler.solver.__class__.__name__)
                    return await self.next_handler.handle(page, captcha_info)
                return None
            
            # Attempt to solve with circuit breaker protection
            try:
                self.logger.info("captcha_handler.handle: attempting to solve captcha", 
                               captcha_type=captcha_type,
                               solver=self.solver.__class__.__name__,
                               circuit_breaker_state=self.circuit_breaker.current_state.value)
                
                solution = await self.circuit_breaker.call(
                    self.solver.solve,
                    page,
                    captcha_info
                )
                
                if solution:
                    self.logger.info("captcha_handler.handle: captcha solved successfully",
                                   solver=self.solver.__class__.__name__,
                                   solution_length=len(solution))
                    trace.add_metadata({"success": True, "solution_length": len(solution)})
                    return solution
                else:
                    self.logger.warning("captcha_handler.handle: solver returned no solution",
                                      solver=self.solver.__class__.__name__)
                    trace.add_metadata({"success": False, "reason": "no_solution"})
                    
            except CircuitBreakerOpen:
                status = self.circuit_breaker.get_status()
                self.logger.warning(
                    "captcha_handler.handle: circuit breaker is open",
                    solver=self.solver.__class__.__name__,
                    failure_count=status.get('failure_count'),
                    last_failure=status.get('last_failure_time'),
                    recovery_time=status.get('recovery_time')
                )
                trace.add_metadata({"success": False, "reason": "circuit_breaker_open"})
            except Exception as e:
                self.logger.error(
                    "captcha_handler.handle: error solving captcha",
                    solver=self.solver.__class__.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                trace.add_metadata({
                    "success": False, 
                    "reason": "exception",
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            
            # If failed or couldn't solve, pass to the next handler
            if self.next_handler:
                self.logger.info("captcha_handler.handle: passing to next handler after failure",
                               current_solver=self.solver.__class__.__name__,
                               next_solver=self.next_handler.solver.__class__.__name__)
                return await self.next_handler.handle(page, captcha_info)
            
            self.logger.debug("captcha_handler.handle: no more handlers in chain")
            return None
    
    def set_next(self, handler: 'CaptchaSolverHandler') -> 'CaptchaSolverHandler':
        """Set the next handler in the chain.
        
        Args:
            handler: The next handler to be called if this one fails.
            
        Returns:
            The provided handler for method chaining.
        """
        self.next_handler = handler
        return handler


class CaptchaChain:
    """Chain of Responsibility for captcha resolution.
    
    This class manages a chain of captcha solvers, each protected by a circuit breaker.
    When a captcha needs to be solved, the chain tries each solver in sequence
    until one successfully solves it or all solvers have been exhausted.
    """
    
    def __init__(self):
        """Initialize an empty chain."""
        self._first_handler: Optional[CaptchaSolverHandler] = None
        self._handlers: List[CaptchaSolverHandler] = []
        self.logger = logger.bind(component="captcha_chain")
    
    def add_solver(
        self,
        solver: ICaptchaSolver,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ) -> 'CaptchaChain':
        """Add a solver to the chain.
        
        Solvers are added in order and will be tried sequentially.
        Each solver is automatically wrapped with a circuit breaker.
        
        Args:
            solver: The captcha solver implementation to add.
            circuit_breaker_config: Optional custom circuit breaker configuration.
                                  If not provided, default configuration is used.
            
        Returns:
            Self for method chaining.
        """
        circuit_breaker = CircuitBreaker(
            name=solver.__class__.__name__,
            config=circuit_breaker_config or CircuitBreakerConfig()
        )
        
        handler = CaptchaSolverHandler(solver, circuit_breaker)
        
        if not self._first_handler:
            self._first_handler = handler
        else:
            # Add to the end of the chain
            last_handler = self._handlers[-1]
            last_handler.set_next(handler)
        
        self._handlers.append(handler)
        
        self.logger.info(
            "captcha_chain.add_solver: solver added to chain",
            solver=solver.__class__.__name__,
            position=len(self._handlers),
            circuit_breaker_config={
                "failure_threshold": circuit_breaker.config.failure_threshold,
                "recovery_timeout": str(circuit_breaker.config.recovery_timeout),
                "success_threshold": circuit_breaker.config.success_threshold
            }
        )
        
        return self
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Attempt to solve a captcha using the chain.
        
        This method starts the chain of responsibility, passing the captcha
        through each solver until one successfully solves it.
        
        Args:
            page: The page interface containing the captcha.
            captcha_info: Dictionary with captcha details (type, sitekey, etc.).
            
        Returns:
            The captcha solution string if any solver succeeds, None if all fail.
        """
        if not self._first_handler:
            self.logger.error("captcha_chain.solve: no solvers in chain")
            return None
        
        self.logger.info(
            "captcha_chain.solve: starting captcha resolution",
            captcha_type=captcha_info.get("type", "unknown"),
            solvers_count=len(self._handlers),
            solvers=[h.solver.__class__.__name__ for h in self._handlers]
        )
        
        solution = await self._first_handler.handle(page, captcha_info)
        
        if solution:
            self.logger.info("captcha_chain.solve: captcha resolved successfully",
                           captcha_type=captcha_info.get("type", "unknown"))
        else:
            self.logger.error("captcha_chain.solve: captcha not resolved by any solver",
                            captcha_type=captcha_info.get("type", "unknown"),
                            solvers_tried=len(self._handlers))
        
        return solution
    
    def get_status(self) -> List[Dict[str, Any]]:
        """Get the status of all circuit breakers in the chain.
        
        This is useful for monitoring the health of the captcha solving services.
        
        Returns:
            List of dictionaries containing circuit breaker status information
            (name, state, failure count, last failure time, etc.).
        """
        return [
            handler.circuit_breaker.get_status()
            for handler in self._handlers
        ]