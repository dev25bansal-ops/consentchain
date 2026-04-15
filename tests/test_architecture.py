"""Tests for architecture components: Cache, Circuit Breaker, Graceful Shutdown, Events."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
import asyncio


class TestCacheService:
    """Tests for the caching layer."""

    def test_cache_key_generation(self):
        from api.cache import CacheKey

        consent_key = CacheKey.consent("consent-123")
        assert "consent" in consent_key
        assert "consent-123" in consent_key

        principal_key = CacheKey.principal_consents("user-456", page=1)
        assert "principal" in principal_key
        assert "user-456" in principal_key

        fiduciary_key = CacheKey.fiduciary("fid-789")
        assert "fiduciary" in fiduciary_key
        assert "fid-789" in fiduciary_key

    @pytest.mark.asyncio
    async def test_cache_set_and_get_local(self):
        """Test local cache when Redis not available."""
        from api.cache import CacheService

        cache = CacheService()

        await cache.set("test-key", {"data": "value"}, ttl=60)
        result = await cache.get("test-key")

        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache deletion."""
        from api.cache import CacheService

        cache = CacheService()

        await cache.set("delete-test", "value", ttl=60)
        assert await cache.get("delete-test") == "value"

        await cache.delete("delete-test")
        assert await cache.get("delete-test") is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self):
        """Test that cache entries expire."""
        from api.cache import CacheService

        cache = CacheService()

        await cache.set("expire-test", "value", ttl=0)

        await asyncio.sleep(0.1)

        result = await cache.get("expire-test")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        from api.cache import CacheService

        cache = CacheService()

        await cache.set("stats-key", "value", ttl=60)
        await cache.get("stats-key")
        await cache.get("missing-key")

        stats = cache.get_stats()
        assert stats["sets"] >= 1
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1


class TestCircuitBreaker:
    """Tests for the circuit breaker pattern."""

    def test_circuit_starts_closed(self):
        from api.resilience import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test-service")

        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        from api.resilience import CircuitBreaker, CircuitBreakerOpen, CircuitState

        cb = CircuitBreaker("test-open", failure_threshold=3)

        async def failing_func():
            raise ValueError("Test error")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpen):
            await cb.call(lambda: None)

    @pytest.mark.asyncio
    async def test_circuit_allows_successful_calls(self):
        from api.resilience import CircuitBreaker

        cb = CircuitBreaker("test-success")

        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"

        stats = cb.get_stats()
        assert stats["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_circuit_timeout(self):
        from api.resilience import CircuitBreaker, CircuitBreakerTimeout

        cb = CircuitBreaker("test-timeout", timeout=0.1)

        async def slow_func():
            await asyncio.sleep(1)
            return "done"

        with pytest.raises(CircuitBreakerTimeout):
            await cb.call(slow_func)

    def test_circuit_stats(self):
        from api.resilience import CircuitBreaker

        cb = CircuitBreaker("test-stats", failure_threshold=10, timeout=30)

        stats = cb.get_stats()

        assert stats["name"] == "test-stats"
        assert stats["state"] == "closed"
        assert stats["config"]["failure_threshold"] == 10
        assert stats["config"]["timeout"] == 30


class TestGracefulShutdown:
    """Tests for graceful shutdown handling."""

    def test_shutdown_starts_running(self):
        from api.lifecycle import GracefulShutdown, ShutdownPhase

        shutdown = GracefulShutdown()

        assert shutdown.phase == ShutdownPhase.RUNNING
        assert shutdown.is_shutting_down is False

    @pytest.mark.asyncio
    async def test_request_tracking(self):
        from api.lifecycle import GracefulShutdown

        shutdown = GracefulShutdown()

        async with shutdown.request_context():
            stats = shutdown.get_stats()
            assert stats["active_requests"] == 1

        stats = shutdown.get_stats()
        assert stats["active_requests"] == 0
        assert stats["completed_requests"] == 1

    @pytest.mark.asyncio
    async def test_reject_requests_during_shutdown(self):
        from api.lifecycle import GracefulShutdown, ShutdownPhase

        shutdown = GracefulShutdown()
        shutdown._stats.phase = ShutdownPhase.SHUTDOWN_REQUESTED

        with pytest.raises(RuntimeError, match="shutting down"):
            async with shutdown.request_context():
                pass

    def test_handler_registration(self):
        from api.lifecycle import GracefulShutdown

        shutdown = GracefulShutdown()

        async def cleanup_db():
            pass

        async def cleanup_redis():
            pass

        shutdown.register_handler("database", cleanup_db)
        shutdown.register_handler("redis", cleanup_redis)

        stats = shutdown.get_stats()
        assert stats["registered_handlers"] == 2

    def test_shutdown_stats(self):
        from api.lifecycle import GracefulShutdown

        shutdown = GracefulShutdown()

        stats = shutdown.get_stats()

        assert "phase" in stats
        assert "active_requests" in stats
        assert "completed_requests" in stats
        assert "registered_handlers" in stats


class TestEventBus:
    """Tests for event-driven architecture."""

    def test_event_creation(self):
        from api.events import Event, EventType

        event = Event(
            type=EventType.CONSENT_GRANTED,
            data={"consent_id": "123", "principal_id": "user-1"},
        )

        assert event.type == EventType.CONSENT_GRANTED
        assert event.data["consent_id"] == "123"
        assert event.id is not None
        assert event.timestamp is not None

    def test_event_serialization(self):
        from api.events import Event, EventType

        event = Event(
            type=EventType.CONSENT_REVOKED,
            data={"consent_id": "456"},
            metadata={"reason": "user_request"},
        )

        event_dict = event.to_dict()
        assert event_dict["type"] == "consent.revoked"
        assert event_dict["data"]["consent_id"] == "456"

        event_json = event.to_json()
        assert '"consent_id": "456"' in event_json

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_publish(self):
        from api.events import EventBus, Event, EventType

        bus = EventBus()
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        bus.subscribe(EventType.CONSENT_GRANTED, handler)

        event = Event(
            type=EventType.CONSENT_GRANTED,
            data={"consent_id": "789"},
        )

        await bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].data["consent_id"] == "789"

    @pytest.mark.asyncio
    async def test_event_bus_wildcard(self):
        from api.events import EventBus, Event, EventType

        bus = EventBus()
        all_events = []

        async def wildcard_handler(event: Event):
            all_events.append(event)

        bus.subscribe_all(wildcard_handler)

        await bus.publish(Event(type=EventType.CONSENT_GRANTED, data={"id": "1"}))
        await bus.publish(Event(type=EventType.CONSENT_REVOKED, data={"id": "2"}))

        await asyncio.sleep(0.1)

        assert len(all_events) == 2

    def test_event_bus_stats(self):
        from api.events import EventBus, EventType

        bus = EventBus()

        bus.subscribe(EventType.CONSENT_GRANTED, lambda e: None)
        bus.subscribe(EventType.CONSENT_REVOKED, lambda e: None)

        stats = bus.get_stats()

        assert stats["handlers_registered"] == 2
        assert EventType.CONSENT_GRANTED in stats["event_types_subscribed"]


class TestEventQueue:
    """Tests for event queue."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        from api.events import EventQueue, Event, EventType

        queue = EventQueue()

        event = Event(type=EventType.CONSENT_GRANTED, data={"id": "test"})

        await queue.enqueue(event)

        dequeued = await queue.dequeue()

        assert dequeued is not None
        assert dequeued.data["id"] == "test"

    @pytest.mark.asyncio
    async def test_queue_stats(self):
        from api.events import EventQueue, Event, EventType

        queue = EventQueue()

        event = Event(type=EventType.CONSENT_GRANTED, data={})
        await queue.enqueue(event)

        stats = queue.get_stats()

        assert stats["queued"] == 1

    @pytest.mark.asyncio
    async def test_queue_ack_nack(self):
        from api.events import EventQueue, Event, EventType

        queue = EventQueue()

        event = Event(type=EventType.CONSENT_GRANTED, data={})
        await queue.enqueue(event)

        dequeued = await queue.dequeue()

        await queue.ack(dequeued.id)

        stats = queue.get_stats()
        assert stats["processed"] == 1


class TestCacheDecorator:
    """Tests for the @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        from api.cache import cached, get_cache_service

        call_count = 0

        @cached(key_prefix="test_func", ttl=60)
        async def expensive_function(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            return {"result": f"{arg1}-{arg2}"}

        result1 = await expensive_function("a", arg2="b")
        result2 = await expensive_function("a", arg2="b")

        assert result1 == result2
        assert call_count == 1


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    def test_registry_singleton(self):
        from api.resilience import CircuitBreakerRegistry

        registry1 = CircuitBreakerRegistry.get_instance()
        registry2 = CircuitBreakerRegistry.get_instance()

        assert registry1 is registry2

    def test_get_or_create(self):
        from api.resilience import CircuitBreakerRegistry, CircuitState

        registry = CircuitBreakerRegistry.get_instance()

        cb1 = registry.get_or_create("service-a", failure_threshold=10)
        cb2 = registry.get_or_create("service-a")

        assert cb1 is cb2
        assert cb1.failure_threshold == 10

    def test_get_all_stats(self):
        from api.resilience import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry.get_instance()
        registry.get_or_create("stats-service-1")
        registry.get_or_create("stats-service-2")

        all_stats = registry.get_all_stats()

        assert "stats-service-1" in all_stats
        assert "stats-service-2" in all_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
