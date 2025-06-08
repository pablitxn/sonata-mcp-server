"""Tests para la cadena de responsabilidad de captchas."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.captcha import CaptchaChain, CaptchaSolverHandler, CircuitBreakerConfig
from src.captcha.interfaces import ICaptchaSolver


class MockCaptchaSolver(ICaptchaSolver):
    """Mock de un solver de captcha para tests."""
    
    def __init__(self, name: str, can_handle_types: list, solution: str = None):
        self.name = name
        self.can_handle_types = can_handle_types
        self.solution = solution
        self.solve_called = False
    
    def can_handle(self, captcha_type: str) -> bool:
        return captcha_type in self.can_handle_types
    
    async def solve(self, page, captcha_info):
        self.solve_called = True
        return self.solution


class TestCaptchaChain:
    """Tests para la cadena de captchas."""
    
    @pytest.fixture
    def mock_page(self):
        """Mock de una página del browser."""
        return MagicMock()
    
    @pytest.fixture
    def captcha_chain(self):
        """Crea una cadena de captchas vacía."""
        return CaptchaChain()
    
    @pytest.mark.asyncio
    async def test_empty_chain_returns_none(self, captcha_chain, mock_page):
        """Verifica que una cadena vacía devuelva None."""
        result = await captcha_chain.solve(mock_page, {"type": "image"})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_single_solver_success(self, captcha_chain, mock_page):
        """Verifica que un solo solver funcione correctamente."""
        solver = MockCaptchaSolver("solver1", ["image"], "SOLUTION_123")
        captcha_chain.add_solver(solver)
        
        result = await captcha_chain.solve(mock_page, {"type": "image"})
        
        assert result == "SOLUTION_123"
        assert solver.solve_called
    
    @pytest.mark.asyncio
    async def test_chain_finds_correct_solver(self, captcha_chain, mock_page):
        """Verifica que la cadena encuentre el solver correcto."""
        solver1 = MockCaptchaSolver("solver1", ["recaptcha"], None)
        solver2 = MockCaptchaSolver("solver2", ["image"], "IMAGE_SOLUTION")
        solver3 = MockCaptchaSolver("solver3", ["hcaptcha"], None)
        
        captcha_chain.add_solver(solver1)
        captcha_chain.add_solver(solver2)
        captcha_chain.add_solver(solver3)
        
        result = await captcha_chain.solve(mock_page, {"type": "image"})
        
        assert result == "IMAGE_SOLUTION"
        assert not solver1.solve_called  # No puede manejar image
        assert solver2.solve_called
        assert not solver3.solve_called  # No se alcanzó
    
    @pytest.mark.asyncio
    async def test_chain_fallback_on_failure(self, captcha_chain, mock_page):
        """Verifica el fallback cuando un solver falla."""
        # Primer solver puede manejar pero no resuelve
        solver1 = MockCaptchaSolver("solver1", ["image"], None)
        # Segundo solver resuelve exitosamente
        solver2 = MockCaptchaSolver("solver2", ["image"], "FALLBACK_SOLUTION")
        
        captcha_chain.add_solver(solver1)
        captcha_chain.add_solver(solver2)
        
        result = await captcha_chain.solve(mock_page, {"type": "image"})
        
        assert result == "FALLBACK_SOLUTION"
        assert solver1.solve_called
        assert solver2.solve_called
    
    @pytest.mark.asyncio
    async def test_chain_with_exception(self, captcha_chain, mock_page):
        """Verifica que la cadena maneje excepciones correctamente."""
        # Solver que lanza excepción
        failing_solver = MockCaptchaSolver("failing", ["image"], None)
        failing_solver.solve = AsyncMock(side_effect=Exception("Solver error"))
        
        # Solver de respaldo
        backup_solver = MockCaptchaSolver("backup", ["image"], "BACKUP_SOLUTION")
        
        captcha_chain.add_solver(failing_solver)
        captcha_chain.add_solver(backup_solver)
        
        result = await captcha_chain.solve(mock_page, {"type": "image"})
        
        assert result == "BACKUP_SOLUTION"
        assert backup_solver.solve_called
    
    @pytest.mark.asyncio
    async def test_no_solver_can_handle(self, captcha_chain, mock_page):
        """Verifica el comportamiento cuando ningún solver puede manejar el tipo."""
        solver1 = MockCaptchaSolver("solver1", ["recaptcha"], None)
        solver2 = MockCaptchaSolver("solver2", ["hcaptcha"], None)
        
        captcha_chain.add_solver(solver1)
        captcha_chain.add_solver(solver2)
        
        result = await captcha_chain.solve(mock_page, {"type": "funcaptcha"})
        
        assert result is None
        assert not solver1.solve_called
        assert not solver2.solve_called
    
    def test_get_status(self, captcha_chain):
        """Verifica que get_status devuelva información de todos los circuit breakers."""
        solver1 = MockCaptchaSolver("solver1", ["image"], None)
        solver2 = MockCaptchaSolver("solver2", ["recaptcha"], None)
        
        captcha_chain.add_solver(solver1)
        captcha_chain.add_solver(solver2)
        
        status = captcha_chain.get_status()
        
        assert len(status) == 2
        assert status[0]["name"] == "MockCaptchaSolver"
        assert status[1]["name"] == "MockCaptchaSolver"
        assert all(s["state"] == "closed" for s in status)


class TestCaptchaSolverHandler:
    """Tests para el handler individual."""
    
    @pytest.fixture
    def mock_page(self):
        """Mock de una página del browser."""
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_handler_passes_to_next_when_cannot_handle(self, mock_page):
        """Verifica que el handler pase al siguiente cuando no puede manejar."""
        solver1 = MockCaptchaSolver("solver1", ["recaptcha"], None)
        solver2 = MockCaptchaSolver("solver2", ["image"], "IMAGE_SOLUTION")
        
        handler1 = CaptchaSolverHandler(solver1)
        handler2 = CaptchaSolverHandler(solver2)
        handler1.set_next(handler2)
        
        result = await handler1.handle(mock_page, {"type": "image"})
        
        assert result == "IMAGE_SOLUTION"
        assert not solver1.solve_called
        assert solver2.solve_called
    
    @pytest.mark.asyncio
    async def test_handler_circuit_breaker_open(self, mock_page):
        """Verifica que el handler maneje circuit breaker abierto."""
        solver = MockCaptchaSolver("solver", ["image"], None)
        handler = CaptchaSolverHandler(solver)
        
        # Forzar apertura del circuit breaker
        handler.circuit_breaker._state.state = handler.circuit_breaker._state.state.__class__.OPEN
        
        result = await handler.handle(mock_page, {"type": "image"})
        
        assert result is None
        assert not solver.solve_called