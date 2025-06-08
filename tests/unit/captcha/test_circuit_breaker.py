"""Tests for Circuit Breaker."""

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
    """Tests for Circuit Breaker."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Creates a circuit breaker for tests."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=timedelta(seconds=1),
            success_threshold=2,
            max_consecutive_failures=2
        )
        return CircuitBreaker("test_service", config)
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        """Verifies that the initial state is closed."""
        assert circuit_breaker.is_closed()
        assert not circuit_breaker.is_open()
        assert circuit_breaker.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self, circuit_breaker):
        """Verifies that successful calls keep the circuit closed."""
        async def successful_call():
            return "success"
        
        for _ in range(5):
            result = await circuit_breaker.call(successful_call)
            assert result == "success"
        
        assert circuit_breaker.is_closed()
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failure_threshold(self, circuit_breaker):
        """Verifies that the circuit opens after the failure threshold."""
        async def failing_call():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        assert circuit_breaker.is_closed()
        
        # Second failure - with max_consecutive_failures=2, should open here
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        assert circuit_breaker.is_open()  # Opens due to consecutive failures
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_consecutive_failures(self, circuit_breaker):
        """Verifies that the circuit opens due to consecutive failures."""
        async def failing_call():
            raise Exception("Test failure")
        
        # Two consecutive failures should open the circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Verifies that an open circuit rejects calls."""
        async def failing_call():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
        
        # Try to call with open circuit
        with pytest.raises(CircuitBreakerOpen):
            await circuit_breaker.call(failing_call)
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Verifies transition to half-open after timeout."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # The next call should be attempted (half-open)
        result = await circuit_breaker.call(successful_call)
        assert result == "success"
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_threshold(self, circuit_breaker):
        """Verifies that the circuit closes after the success threshold."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Esperar recovery timeout
        await asyncio.sleep(1.1)
        
        # Two successful calls should close the circuit
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
        
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.is_closed()
    
    @pytest.mark.asyncio
    async def test_half_open_returns_to_open_on_failure(self, circuit_breaker):
        """Verifies that half-open returns to open on failure."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def successful_call():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Esperar recovery timeout
        await asyncio.sleep(1.1)
        
        # Initial success to transition to half-open
        await circuit_breaker.call(successful_call)
        assert circuit_breaker.current_state == CircuitState.HALF_OPEN
        
        # Failure in half-open should return to open
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_call)
        
        assert circuit_breaker.is_open()
    
    def test_get_status(self, circuit_breaker):
        """Verifies that get_status returns correct information."""
        status = circuit_breaker.get_status()
        
        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["consecutive_failures"] == 0
        assert status["last_failure_time"] is None