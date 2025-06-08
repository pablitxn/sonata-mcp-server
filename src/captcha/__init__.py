"""Captcha handling module.

This module provides a comprehensive captcha solving system with multiple solver backends,
circuit breaker pattern for resilience, and chain of responsibility pattern for fallback handling.

Main components:
- CaptchaChain: Orchestrates multiple captcha solvers with automatic fallback
- CaptchaSolverHandler: Wraps individual solvers with circuit breaker protection
- CircuitBreaker: Prevents cascading failures when captcha services are unavailable
- ICaptchaSolver: Base interface for implementing captcha solver services
- Multiple solver implementations: CapSolverAI, TwoCaptchaSolver, AntiCaptchaSolver
"""

# Chain of Responsibility pattern implementation for captcha solving
from .chain import CaptchaChain, CaptchaSolverHandler

# Circuit breaker pattern for resilient external service calls
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen, CircuitState

# Base interface for captcha solver implementations
from .interfaces import ICaptchaSolver

# Concrete captcha solver implementations for different services
from .solvers import CapSolverAI, TwoCaptchaSolver, AntiCaptchaSolver

# Public API exports
__all__ = [
    # Chain of responsibility components
    "CaptchaChain", 
    "CaptchaSolverHandler",
    # Circuit breaker components
    "CircuitBreaker", 
    "CircuitBreakerConfig", 
    "CircuitBreakerOpen",
    "CircuitState",
    # Base interface
    "ICaptchaSolver",
    # Concrete solver implementations
    "CapSolverAI", 
    "TwoCaptchaSolver", 
    "AntiCaptchaSolver"
]