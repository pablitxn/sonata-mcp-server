"""Circuit Breaker para manejo resiliente de servicios de captcha."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Estados del circuit breaker."""
    CLOSED = "closed"  # Normal, permite llamadas
    OPEN = "open"      # Falla, bloquea llamadas
    HALF_OPEN = "half_open"  # Prueba si el servicio se recuperó


@dataclass
class CircuitBreakerConfig:
    """Configuración del circuit breaker."""
    failure_threshold: int = 5  # Número de fallas para abrir el circuito
    recovery_timeout: timedelta = timedelta(seconds=60)  # Tiempo antes de probar de nuevo
    success_threshold: int = 3  # Éxitos necesarios para cerrar desde half-open
    max_consecutive_failures: int = 3  # Fallas consecutivas permitidas


@dataclass
class CircuitBreakerState:
    """Estado interno del circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)


class CircuitBreaker:
    """Circuit breaker para proteger servicios externos."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Inicializa el circuit breaker.
        
        Args:
            name: Nombre del servicio protegido.
            config: Configuración del circuit breaker.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(circuit_breaker=name)
    
    @property
    def current_state(self) -> CircuitState:
        """Estado actual del circuit breaker."""
        return self._state.state
    
    def is_open(self) -> bool:
        """Verifica si el circuito está abierto."""
        return self._state.state == CircuitState.OPEN
    
    def is_closed(self) -> bool:
        """Verifica si el circuito está cerrado."""
        return self._state.state == CircuitState.CLOSED
    
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transiciona a un nuevo estado.
        
        Args:
            new_state: Nuevo estado del circuito.
        """
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = datetime.now()
        
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
        """Verifica si debería intentar resetear el circuito.
        
        Returns:
            True si ha pasado suficiente tiempo desde la última falla.
        """
        if (self._state.last_failure_time and 
            datetime.now() - self._state.last_failure_time >= self.config.recovery_timeout):
            return True
        return False
    
    async def _record_success(self) -> None:
        """Registra una llamada exitosa."""
        async with self._lock:
            self._state.consecutive_failures = 0
            
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def _record_failure(self) -> None:
        """Registra una llamada fallida."""
        async with self._lock:
            self._state.failure_count += 1
            self._state.consecutive_failures += 1
            self._state.last_failure_time = datetime.now()
            
            if self._state.state == CircuitState.CLOSED:
                if (self._state.failure_count >= self.config.failure_threshold or
                    self._state.consecutive_failures >= self.config.max_consecutive_failures):
                    await self._transition_to(CircuitState.OPEN)
            elif self._state.state == CircuitState.HALF_OPEN:
                await self._transition_to(CircuitState.OPEN)
    
    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Ejecuta una función protegida por el circuit breaker.
        
        Args:
            func: Función a ejecutar.
            *args: Argumentos posicionales.
            **kwargs: Argumentos con nombre.
            
        Returns:
            Resultado de la función.
            
        Raises:
            CircuitBreakerOpen: Si el circuito está abierto.
        """
        async with self._lock:
            if self._state.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is open"
                    )
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del circuit breaker.
        
        Returns:
            Información del estado actual.
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
    """Excepción cuando el circuit breaker está abierto."""
    pass