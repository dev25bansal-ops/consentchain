"""Circuit Breaker Pattern for External Service Calls.

Prevents cascade failures by:
- Tracking failures and opening circuit when threshold exceeded
- Allowing periodic test requests during open state
- Automatically recovering when service becomes healthy
"""

from typing import Optional, Callable, Any, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStats:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_failure_error: Optional[str] = None
    last_success_time: Optional[datetime] = None
    state_changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreaker:
    """
    Circuit Breaker implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast
    - HALF_OPEN: Testing if service recovered

    Configuration:
    - failure_threshold: Number of failures before opening (default: 5)
    - recovery_timeout: Seconds to wait before trying half-open (default: 30)
    - success_threshold: Successes in half-open to close (default: 3)
    - timeout: Request timeout in seconds (default: 10)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        success_threshold: int = 3,
        timeout: int = 10,
        on_state_change: Optional[Callable[[str, CircuitState], None]] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is in half-open state (testing)."""
        return self._state == CircuitState.HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitBreakerOpen: When circuit is open
            CircuitBreakerTimeout: When request times out
            Exception: Original exception from function
        """
        async with self._lock:
            await self._check_state_transition()

            if self._state == CircuitState.OPEN:
                logger.warning(f"Circuit {self.name} is open - failing fast")
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Last error: {self._stats.last_failure_error}"
                )

        try:
            self._stats.total_calls += 1

            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout,
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)

            await self._record_success()
            return result

        except asyncio.TimeoutError:
            await self._record_failure(f"Timeout after {self.timeout}s")
            raise CircuitBreakerTimeout(f"Request to '{self.name}' timed out after {self.timeout}s")
        except Exception as e:
            await self._record_failure(str(e))
            raise

    async def _check_state_transition(self):
        """Check and handle state transitions."""
        if self._state == CircuitState.OPEN:
            time_since_open = (datetime.now(timezone.utc) - self._stats.state_changed_at).total_seconds()

            if time_since_open >= self.recovery_timeout:
                logger.info(f"Circuit {self.name} entering half-open state")
                await self._transition_to(CircuitState.HALF_OPEN)

    async def _record_success(self):
        """Record a successful call."""
        self._stats.successful_calls += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = datetime.now(timezone.utc)

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1

            if self._half_open_successes >= self.success_threshold:
                logger.info(f"Circuit {self.name} closing - service recovered")
                await self._transition_to(CircuitState.CLOSED)

    async def _record_failure(self, error: str):
        """Record a failed call."""
        self._stats.failed_calls += 1
        self._stats.consecutive_failures += 1
        self._stats.last_failure_time = datetime.now(timezone.utc)
        self._stats.last_failure_error = error

        logger.warning(
            f"Circuit {self.name} failure {self._stats.consecutive_failures}/"
            f"{self.failure_threshold}: {error}"
        )

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name} re-opening - test request failed")
            await self._transition_to(CircuitState.OPEN)

        elif self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.failure_threshold:
                logger.error(
                    f"Circuit {self.name} opening - threshold exceeded "
                    f"({self.failure_threshold} consecutive failures)"
                )
                await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changed_at = datetime.now(timezone.utc)

        if new_state == CircuitState.CLOSED:
            self._half_open_successes = 0
            self._stats.consecutive_failures = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        logger.info(f"Circuit {self.name} transitioned: {old_state.value} -> {new_state.value}")

        if self.on_state_change:
            try:
                self.on_state_change(self.name, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "consecutive_failures": self._stats.consecutive_failures,
            "last_failure_time": self._stats.last_failure_time.isoformat()
            if self._stats.last_failure_time
            else None,
            "last_failure_error": self._stats.last_failure_error,
            "last_success_time": self._stats.last_success_time.isoformat()
            if self._stats.last_success_time
            else None,
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "success_threshold": self.success_threshold,
                "timeout": self.timeout,
            },
        }

    async def reset(self):
        """Reset the circuit breaker to closed state."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            self._stats = CircuitStats()


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreakerTimeout(Exception):
    """Raised when request times out through circuit breaker."""

    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _instance: Optional["CircuitBreakerRegistry"] = None

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create(
        self,
        name: str,
        **kwargs,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, **kwargs)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers."""
        return {name: cb.get_stats() for name, cb in self._breakers.items()}

    async def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            await cb.reset()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    success_threshold: int = 3,
    timeout: int = 10,
):
    """Decorator to wrap function with circuit breaker."""

    def decorator(func: Callable) -> Callable:
        registry = CircuitBreakerRegistry.get_instance()
        cb = registry.get_or_create(
            name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout,
        )

        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get a circuit breaker by name."""
    return CircuitBreakerRegistry.get_instance().get(name)


def get_all_circuit_stats() -> Dict[str, Dict[str, Any]]:
    """Get stats for all circuit breakers."""
    return CircuitBreakerRegistry.get_instance().get_all_stats()
