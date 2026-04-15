"""Resilience patterns for ConsentChain.

Includes:
- Circuit Breaker for external services
- Retry with exponential backoff
- Timeout handling
- Bulkhead isolation
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpen,
    CircuitBreakerTimeout,
    CircuitBreakerRegistry,
    circuit_breaker,
    get_circuit_breaker,
    get_all_circuit_stats,
)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpen",
    "CircuitBreakerTimeout",
    "CircuitBreakerRegistry",
    "circuit_breaker",
    "get_circuit_breaker",
    "get_all_circuit_stats",
]
