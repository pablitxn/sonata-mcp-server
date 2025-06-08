"""Tests para el Circuit Breaker."""

import asyncio
from datetime import timedelta

import pytest

from src.captcha import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
)


class TestCircuitBreaker:
    """Tests para el Circuit Breaker."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Crea un circuit breaker para tests."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=timedelta(seconds=1),
            success_threshold=2,
            max_consecutive_failures=2
        )
        return CircuitBreaker("test_service", config)
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        """Verifica que el estado inicial sea cerrado."""
        assert circuit_breaker.is_closed()
        assert not circuit_breaker.is_open()
        assert circuit_breaker.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self, circuit_breaker):
        """Verifica que llamadas exitosas mantengan el circuito cerrado."""
        async def successful_call():
            return "success"
        
        for _ in range(5):
            result = await circuit_breaker.call(successful_call)
            assert result == "success"
        
        assert circuit_breaker.is_closed()
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failure_threshold(self, circuit_breaker):
        """Verifica que el circuito se abra después del umbral de fallas."""
        async def failing_call():
            raise Exception("Test failure")
        
        # Primera falla
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        assert circuit_breaker.is_closed()
        
        # Segunda falla - con max_consecutive_failures=2, debería abrir aquí
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        assert circuit_breaker.is_open()  # Se abre por fallas consecutivas
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_consecutive_failures(self, circuit_breaker):
        """Verifica que el circuito se abra por fallas consecutivas."""
        async def failing_call():
            raise Exception("Test failure")
        
        # Dos fallas consecutivas deberían abrir el circuito
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Verifica que un circuito abierto rechace llamadas."""
        async def failing_call():
            raise Exception("Test failure")
        
        # Abrir el circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
        
        # Intentar llamar con circuito abierto
        with pytest.raises(CircuitBreakerOpen):
            await circuit_breaker.call(failing_call)
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Verifica la transición a half-open después del timeout."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Abrir el circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Esperar el recovery timeout
        await asyncio.sleep(1.1)
        
        # La próxima llamada debería intentarse (half-open)
        result = await circuit_breaker.call(successful_call)
        assert result == "success"
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_threshold(self, circuit_breaker):
        """Verifica que el circuito se cierre después del umbral de éxitos."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Abrir el circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Esperar recovery timeout
        await asyncio.sleep(1.1)
        
        # Dos llamadas exitosas deberían cerrar el circuito
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
        
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.is_closed()
    
    @pytest.mark.asyncio
    async def test_half_open_returns_to_open_on_failure(self, circuit_breaker):
        """Verifica que half-open vuelva a open en caso de falla."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Abrir el circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Esperar recovery timeout
        await asyncio.sleep(1.1)
        
        # Éxito inicial para pasar a half-open
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
        
        # Falla en half-open debería volver a open
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
    
    def test_get_status(self, circuit_breaker):
        """Verifica que get_status devuelva información correcta."""
        status = circuit_breaker.get_status()
        
        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["consecutive_failures"] == 0
        assert status["last_failure_time"] is None