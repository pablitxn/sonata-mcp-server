"""Chain of Responsibility para resolución de captchas."""

from typing import Any, Dict, List, Optional

import structlog

from src.browser.interfaces import IPage
from src.connectors.afip.interfaces import ICaptchaSolver
from src.captcha.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen

logger = structlog.get_logger()


class CaptchaSolverHandler:
    """Handler para un resolver de captcha con circuit breaker."""
    
    def __init__(
        self,
        solver: ICaptchaSolver,
        circuit_breaker: Optional[CircuitBreaker] = None,
        next_handler: Optional['CaptchaSolverHandler'] = None
    ):
        """Inicializa el handler.
        
        Args:
            solver: Resolver de captcha.
            circuit_breaker: Circuit breaker para el solver.
            next_handler: Siguiente handler en la cadena.
        """
        self.solver = solver
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name=solver.__class__.__name__,
            config=CircuitBreakerConfig()
        )
        self.next_handler = next_handler
        self.logger = logger.bind(solver=solver.__class__.__name__)
    
    async def handle(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Maneja la resolución del captcha.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            Solución del captcha o None.
        """
        captcha_type = captcha_info.get("type", "unknown")
        
        # Verificar si este solver puede manejar el captcha
        if not self.solver.can_handle(captcha_type):
            self.logger.debug("solver_cannot_handle", captcha_type=captcha_type)
            if self.next_handler:
                return await self.next_handler.handle(page, captcha_info)
            return None
        
        # Intentar resolver con circuit breaker
        try:
            self.logger.info("attempting_captcha_solve", captcha_type=captcha_type)
            
            solution = await self.circuit_breaker.call(
                self.solver.solve,
                page,
                captcha_info
            )
            
            if solution:
                self.logger.info("captcha_solved_successfully")
                return solution
            else:
                self.logger.warning("solver_returned_no_solution")
                
        except CircuitBreakerOpen:
            self.logger.warning(
                "circuit_breaker_open",
                status=self.circuit_breaker.get_status()
            )
        except Exception as e:
            self.logger.error(
                "captcha_solve_error",
                error=str(e),
                exc_info=True
            )
        
        # Si falló o no pudo resolver, pasar al siguiente
        if self.next_handler:
            return await self.next_handler.handle(page, captcha_info)
        
        return None
    
    def set_next(self, handler: 'CaptchaSolverHandler') -> 'CaptchaSolverHandler':
        """Establece el siguiente handler en la cadena.
        
        Args:
            handler: Siguiente handler.
            
        Returns:
            El handler actual para encadenamiento.
        """
        self.next_handler = handler
        return handler


class CaptchaChain:
    """Cadena de responsabilidad para resolución de captchas."""
    
    def __init__(self):
        """Inicializa la cadena vacía."""
        self._first_handler: Optional[CaptchaSolverHandler] = None
        self._handlers: List[CaptchaSolverHandler] = []
        self.logger = logger.bind(component="captcha_chain")
    
    def add_solver(
        self,
        solver: ICaptchaSolver,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ) -> 'CaptchaChain':
        """Agrega un solver a la cadena.
        
        Args:
            solver: Resolver de captcha.
            circuit_breaker_config: Configuración del circuit breaker.
            
        Returns:
            La cadena para encadenamiento.
        """
        circuit_breaker = CircuitBreaker(
            name=solver.__class__.__name__,
            config=circuit_breaker_config or CircuitBreakerConfig()
        )
        
        handler = CaptchaSolverHandler(solver, circuit_breaker)
        
        if not self._first_handler:
            self._first_handler = handler
        else:
            # Agregar al final de la cadena
            last_handler = self._handlers[-1]
            last_handler.set_next(handler)
        
        self._handlers.append(handler)
        
        self.logger.info(
            "solver_added_to_chain",
            solver=solver.__class__.__name__,
            position=len(self._handlers)
        )
        
        return self
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Intenta resolver un captcha usando la cadena.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            Solución del captcha o None si ningún solver pudo resolverlo.
        """
        if not self._first_handler:
            self.logger.error("no_solvers_in_chain")
            return None
        
        self.logger.info(
            "starting_captcha_resolution",
            captcha_type=captcha_info.get("type", "unknown"),
            solvers_count=len(self._handlers)
        )
        
        solution = await self._first_handler.handle(page, captcha_info)
        
        if solution:
            self.logger.info("captcha_resolved_by_chain")
        else:
            self.logger.error("captcha_not_resolved_by_any_solver")
        
        return solution
    
    def get_status(self) -> List[Dict[str, Any]]:
        """Obtiene el estado de todos los circuit breakers.
        
        Returns:
            Lista con el estado de cada circuit breaker.
        """
        return [
            handler.circuit_breaker.get_status()
            for handler in self._handlers
        ]