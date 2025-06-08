"""Modulo de manejo de captchas."""

from .chain import CaptchaChain, CaptchaSolverHandler
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen, CircuitState
from .interfaces import ICaptchaSolver
from .solvers import CapSolverAI, TwoCaptchaSolver, AntiCaptchaSolver

__all__ = [
    "CaptchaChain", 
    "CaptchaSolverHandler",
    "CircuitBreaker", 
    "CircuitBreakerConfig", 
    "CircuitBreakerOpen",
    "CircuitState",
    "ICaptchaSolver",
    "CapSolverAI", 
    "TwoCaptchaSolver", 
    "AntiCaptchaSolver"
]