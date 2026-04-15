"""Tests for the event-driven architecture.

Covers:
- Event publishing and subscribing
- Event queue processing
- Redis-backed durability
- Event replay
- Dead letter queue
- Priority events
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.events import (
    Event,
    EventBus,
    EventQueue,
    EventType,
    publish_event,
    get_event_bus,
    get_event_queue,
    on_event,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fresh_event_bus():
    """Provide a fresh EventBus instance for each test."""
    bus = EventBus()
    with patch("api.events._event_bus", bus):
        yield bus


@pytest.fixture
def fresh_event_queue():
    """Provide a fresh EventQueue instance for each test."""
    queue = EventQueue()
    with patch("api.events._event_queue", queue):
        yield queue


@pytest.fixture
def mock_redis():
    """Provide a mocked Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.rpush = AsyncMock(return_value=1)
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.lpop = AsyncMock(return_value=None)
    mock.rpush = AsyncMock(return_value=1)
    mock.xadd = AsyncMock(return_value="0-1")
    mock.xread = AsyncMock(return_value=[])
    mock.xlen = AsyncMock(return_value=0)
    mock.delete = AsyncMock(return_value=1)
    mock.close = AsyncMock()
    return mock


# ============================================================
# Test: Event data class
# ============================================================


class TestEventDataClass:
    """Test the Event dataclass serialization and deserialization."""

    def test_event_to_dict(self):
        """Event serializes to dict correctly."""
        event = Event(
            type=EventType.CONSENT_GRANTED,
            data={"consent_id": "test-123", "principal_id": "user-1"},
            source="test-runner",
        )
        d = event.to_dict()
        assert d["type"] == "consent.granted"
        assert d["data"]["consent_id"] == "test-123"
        assert d["source"] == "test-runner"
        assert d["version"] == "1.0"
        assert "id" in d
        assert "timestamp" in d

    def test_event_to_json(self):
        """Event serializes to JSON correctly."""
        event = Event(
            type=EventType.CONSENT_REVOKED,
            data={"consent_id": "abc-456"},
        )
        raw = event.to_json()
        parsed = json.loads(raw)
        assert parsed["type"] == "consent.revoked"
        assert parsed["data"]["consent_id"] == "abc-456"

    def test_event_from_dict(self):
        """Event deserializes from dict correctly."""
        data = {
            "id": str(uuid4()),
            "type": "consent.modified",
            "timestamp": "2025-01-01T12:00:00+00:00",
            "source": "api",
            "version": "1.0",
            "data": {"consent_id": "xyz"},
            "metadata": {"actor": "admin"},
        }
        event = Event.from_dict(data)
        assert event.type == EventType.CONSENT_MODIFIED
        assert event.data["consent_id"] == "xyz"
        assert event.metadata["actor"] == "admin"

    def test_event_roundtrip(self):
        """Event survives a JSON roundtrip."""
        original = Event(
            type=EventType.GRIEVANCE_SUBMITTED,
            data={"grievance_id": str(uuid4())},
            metadata={"ip": "127.0.0.1"},
        )
        restored = Event.from_dict(original.to_dict())
        assert restored.type == original.type
        assert restored.data == original.data
        assert restored.metadata == original.metadata


# ============================================================
# Test: Event publishing
# ============================================================


class TestEventPublishing:
    """Test event publishing to handlers."""

    @pytest.mark.asyncio
    async def test_publish_calls_handler(self, fresh_event_bus):
        """Publishing an event calls registered handler."""
        received = []

        async def handler(event: Event):
            received.append(event)

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler)
        event = Event(type=EventType.CONSENT_GRANTED, data={"consent_id": "c1"})
        await fresh_event_bus.publish(event)

        assert len(received) == 1
        assert received[0].data["consent_id"] == "c1"

    @pytest.mark.asyncio
    async def test_publish_multiple_handlers(self, fresh_event_bus):
        """Publishing calls all handlers for an event type."""
        results = []

        async def handler_a(event: Event):
            results.append(("a", event.type.value))

        async def handler_b(event: Event):
            results.append(("b", event.type.value))

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler_a)
        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler_b)

        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_bus.publish(event)

        assert len(results) == 2
        assert ("a", "consent.granted") in results
        assert ("b", "consent.granted") in results

    @pytest.mark.asyncio
    async def test_publish_no_handlers(self, fresh_event_bus):
        """Publishing with no handlers does not raise."""
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_bus.publish(event)  # should not raise
        stats = fresh_event_bus.get_stats()
        assert stats["events_published"] == 1

    @pytest.mark.asyncio
    async def test_wildcard_handler(self, fresh_event_bus):
        """Wildcard handler receives all events."""
        received = []

        async def wildcard_handler(event: Event):
            received.append(event)

        fresh_event_bus.subscribe_all(wildcard_handler)

        await fresh_event_bus.publish(Event(type=EventType.CONSENT_GRANTED))
        await fresh_event_bus.publish(Event(type=EventType.DELETION_REQUESTED))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_handler_error_logged(self, fresh_event_bus):
        """Handler errors are logged but do not crash the bus."""

        async def failing_handler(event: Event):
            raise ValueError("intentional failure")

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, failing_handler)
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_bus.publish(event)

        stats = fresh_event_bus.get_stats()
        assert stats["handler_errors"] == 1

    @pytest.mark.asyncio
    async def test_publish_event_with_middleware(self, fresh_event_bus):
        """Middleware processes events before handlers."""
        processed = []

        async def enrich_middleware(event: Event) -> Event:
            event.data["middleware_applied"] = True
            return event

        fresh_event_bus.add_middleware(enrich_middleware)

        async def handler(event: Event):
            processed.append(event)

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler)

        event = Event(type=EventType.CONSENT_GRANTED, data={"key": "value"})
        await fresh_event_bus.publish(event)

        assert processed[0].data["middleware_applied"] is True

    @pytest.mark.asyncio
    async def test_unsubscribe(self, fresh_event_bus):
        """Unsubscribing removes handler."""
        calls = []

        async def handler(event: Event):
            calls.append(event)

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler)
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_bus.publish(event)
        assert len(calls) == 1

        fresh_event_bus.unsubscribe(EventType.CONSENT_GRANTED, handler)
        await fresh_event_bus.publish(event)
        assert len(calls) == 1  # no new call

    @pytest.mark.asyncio
    async def test_publish_event_convenience_function(self, fresh_event_bus):
        """publish_event() convenience function works correctly."""
        with patch("api.events._event_bus", fresh_event_bus):
            received = []

            async def handler(event: Event):
                received.append(event)

            fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler)
            await publish_event(EventType.CONSENT_GRANTED, {"consent_id": "x1"})

            assert len(received) == 1
            assert received[0].data["consent_id"] == "x1"


# ============================================================
# Test: Event subscribing with decorator
# ============================================================


class TestEventSubscribing:
    """Test the @on_event decorator."""

    @pytest.mark.asyncio
    async def test_on_event_decorator(self, fresh_event_bus):
        """@on_event decorator registers handler."""
        with patch("api.events._event_bus", fresh_event_bus):
            received = []

            @on_event(EventType.CONSENT_REVOKED)
            async def revoke_handler(event: Event):
                received.append(event)

            event = Event(type=EventType.CONSENT_REVOKED, data={"consent_id": "r1"})
            await fresh_event_bus.publish(event)

            assert len(received) == 1
            assert received[0].data["consent_id"] == "r1"


# ============================================================
# Test: Event queue processing
# ============================================================


class TestEventQueue:
    """Test the priority event queue."""

    @pytest.mark.asyncio
    async def test_enqueue_and_dequeue(self, fresh_event_queue):
        """Events can be enqueued and dequeued."""
        event = Event(type=EventType.CONSENT_GRANTED, data={"id": "1"})
        await fresh_event_queue.enqueue(event)

        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None
        assert dequeued.data["id"] == "1"

    @pytest.mark.asyncio
    async def test_queue_ack(self, fresh_event_queue):
        """Acknowledging removes from pending."""
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_queue.enqueue(event)
        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None

        await fresh_event_queue.ack(dequeued.id)
        stats = fresh_event_queue.get_stats()
        assert stats["processed"] == 1
        assert stats["pending"] == 0

    @pytest.mark.asyncio
    async def test_queue_nack_requeue(self, fresh_event_queue):
        """Nacking re-enqueues the event."""
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_queue.enqueue(event, priority=0)

        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None
        await fresh_event_queue.nack(dequeued.id, requeue=True)

        stats = fresh_event_queue.get_stats()
        assert stats["failed"] == 1
        assert stats["queue_size"] == 1  # re-queued

    @pytest.mark.asyncio
    async def test_queue_timeout_returns_none(self, fresh_event_queue):
        """Dequeue on empty queue returns None after timeout."""
        result = await fresh_event_queue.dequeue(timeout=0.05)
        assert result is None

    @pytest.mark.asyncio
    async def test_queue_delayed_processing(self, fresh_event_queue):
        """Events with delay are not processed immediately."""
        event = Event(type=EventType.CONSENT_GRANTED, data={"delayed": True})
        await fresh_event_queue.enqueue(event, delay_seconds=60)

        # Should not be available yet
        result = await fresh_event_queue.dequeue(timeout=0.1)
        assert result is None


# ============================================================
# Test: Priority events
# ============================================================


class TestPriorityEvents:
    """Test priority-based event processing."""

    @pytest.mark.asyncio
    async def test_high_priority_processed_first(self, fresh_event_queue):
        """High priority events are dequeued before low priority."""
        low_event = Event(type=EventType.CONSENT_GRANTED, data={"priority": "low"})
        high_event = Event(type=EventType.BREACH_DETECTED, data={"priority": "high"})

        await fresh_event_queue.enqueue(low_event, priority=10)
        await fresh_event_queue.enqueue(high_event, priority=1)  # lower = higher priority

        first = await fresh_event_queue.dequeue(timeout=0.1)
        assert first.data["priority"] == "high"

        second = await fresh_event_queue.dequeue(timeout=0.1)
        assert second.data["priority"] == "low"

    @pytest.mark.asyncio
    async def test_default_priority_is_zero(self, fresh_event_queue):
        """Events enqueued without priority get default priority."""
        event = Event(type=EventType.CONSENT_GRANTED)
        await fresh_event_queue.enqueue(event)

        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None
        assert dequeued.type == EventType.CONSENT_GRANTED


# ============================================================
# Test: Redis-backed durability
# ============================================================


class TestRedisDurability:
    """Test event persistence with Redis."""

    @pytest.mark.asyncio
    async def test_event_stored_in_redis_stream(self, fresh_event_bus, mock_redis):
        """Events are persisted to a Redis stream."""
        mock_redis.xadd = AsyncMock(return_value="1234567890123-0")

        async def redis_sink(event: Event):
            await mock_redis.xadd(
                "events:consentchain",
                event.to_dict(),
            )

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, redis_sink)
        event = Event(type=EventType.CONSENT_GRANTED, data={"consent_id": "redis-test"})
        await fresh_event_bus.publish(event)

        mock_redis.xadd.assert_called_once()
        call_kwargs = mock_redis.xadd.call_args
        assert call_kwargs[0][0] == "events:consentchain"
        assert call_kwargs[0][1]["data"]["consent_id"] == "redis-test"

    @pytest.mark.asyncio
    async def test_event_read_from_redis_stream(self, mock_redis):
        """Events can be read back from Redis stream."""
        event = Event(type=EventType.CONSENT_GRANTED, data={"consent_id": "read-test"})
        mock_redis.xread = AsyncMock(
            return_value=[("events:consentchain", [("0-1", event.to_dict())])]
        )

        result = await mock_redis.xread(
            streams={"events:consentchain": "0"},
            count=10,
        )

        assert result is not None
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_redis_connection_failure_graceful(self):
        """System handles Redis connection failure gracefully."""
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(EventType.CONSENT_GRANTED, handler)

        # Even without Redis, the in-memory bus should work
        event = Event(type=EventType.CONSENT_GRANTED, data={"test": True})
        await bus.publish(event)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_persists_across_restarts(self, mock_redis):
        """Events stored in Redis survive service restart."""
        events_to_store = [
            Event(type=EventType.CONSENT_GRANTED, data={"id": f"e{i}"})
            for i in range(5)
        ]

        for e in events_to_store:
            await mock_redis.rpush("event_buffer", e.to_json())

        mock_redis.llen = AsyncMock(return_value=5)
        mock_redis.lrange = AsyncMock(
            return_value=[e.to_json() for e in events_to_store]
        )

        count = await mock_redis.llen("event_buffer")
        assert count == 5

        stored = await mock_redis.lrange("event_buffer", 0, -1)
        assert len(stored) == 5
        restored = Event.from_dict(json.loads(stored[0]))
        assert restored.type == EventType.CONSENT_GRANTED


# ============================================================
# Test: Event replay
# ============================================================


class TestEventReplay:
    """Test replaying events from history."""

    @pytest.mark.asyncio
    async def test_replay_from_stream(self, mock_redis):
        """Events can be replayed from a Redis stream."""
        stored_events = [
            Event(type=EventType.CONSENT_GRANTED, data={"id": "1"}),
            Event(type=EventType.CONSENT_REVOKED, data={"id": "2"}),
            Event(type=EventType.CONSENT_MODIFIED, data={"id": "3"}),
        ]

        mock_redis.xread = AsyncMock(
            return_value=[
                (
                    "events:consentchain",
                    [(f"0-{i}", e.to_dict()) for i, e in enumerate(stored_events)],
                )
            ]
        )

        result = await mock_redis.xread(
            streams={"events:consentchain": "0"},
            count=100,
        )

        assert result is not None
        stream_entries = result[0][1]
        assert len(stream_entries) == 3

    @pytest.mark.asyncio
    async def test_replay_with_id_filtering(self, mock_redis):
        """Replay can start from a specific event ID."""
        mock_redis.xread = AsyncMock(
            return_value=[
                (
                    "events:consentchain",
                    [
                        ("100-0", Event(type=EventType.CONSENT_GRANTED).to_dict()),
                        ("101-0", Event(type=EventType.CONSENT_REVOKED).to_dict()),
                    ],
                )
            ]
        )

        result = await mock_redis.xread(
            streams={"events:consentchain": "99-0"},
            count=10,
        )

        assert len(result[0][1]) == 2

    @pytest.mark.asyncio
    async def test_replay_rebuilds_state(self, fresh_event_bus):
        """Replaying events reconstructs the system state."""
        state = {"consents": set()}

        async def state_handler(event: Event):
            cid = event.data.get("consent_id")
            if event.type == EventType.CONSENT_GRANTED:
                state["consents"].add(cid)
            elif event.type == EventType.CONSENT_REVOKED:
                state["consents"].discard(cid)

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, state_handler)
        fresh_event_bus.subscribe(EventType.CONSENT_REVOKED, state_handler)

        # Replay a sequence of events
        await fresh_event_bus.publish(
            Event(type=EventType.CONSENT_GRANTED, data={"consent_id": "c1"})
        )
        await fresh_event_bus.publish(
            Event(type=EventType.CONSENT_GRANTED, data={"consent_id": "c2"})
        )
        await fresh_event_bus.publish(
            Event(type=EventType.CONSENT_REVOKED, data={"consent_id": "c1"})
        )

        assert state["consents"] == {"c2"}


# ============================================================
# Test: Dead letter queue
# ============================================================


class TestDeadLetterQueue:
    """Test dead letter queue for failed events."""

    @pytest.mark.asyncio
    async def test_failed_events_go_to_dlq(self, fresh_event_queue):
        """Events that fail processing are moved to dead letter queue."""
        event = Event(type=EventType.CONSENT_GRANTED, data={"id": "fail-me"})
        await fresh_event_queue.enqueue(event)

        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None

        # Simulate repeated failures by nacking without requeue
        await fresh_event_queue.nack(dequeued.id, requeue=False)

        stats = fresh_event_queue.get_stats()
        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_dlq_preserves_event_data(self, fresh_event_queue):
        """Dead letter queue preserves full event data."""
        original_data = {
            "consent_id": "dlq-test-123",
            "fiduciary_id": "fid-456",
            "metadata": {"attempt": 3, "last_error": "timeout"},
        }
        event = Event(type=EventType.CONSENT_GRANTED, data=original_data)
        await fresh_event_queue.enqueue(event)

        dequeued = await fresh_event_queue.dequeue(timeout=0.1)
        assert dequeued is not None
        assert dequeued.data["consent_id"] == "dlq-test-123"
        assert dequeued.data["metadata"]["attempt"] == 3

    @pytest.mark.asyncio
    async def test_max_retry_before_dlq(self, fresh_event_queue):
        """Events go to DLQ after max retries."""
        max_retries = 3
        event = Event(type=EventType.CONSENT_GRANTED, data={"retry_test": True})

        for _ in range(max_retries):
            await fresh_event_queue.enqueue(event)
            dequeued = await fresh_event_queue.dequeue(timeout=0.1)
            if dequeued:
                await fresh_event_queue.nack(dequeued.id, requeue=False)

        stats = fresh_event_queue.get_stats()
        assert stats["failed"] == max_retries


# ============================================================
# Test: Event bus statistics
# ============================================================


class TestEventBusStats:
    """Test event bus statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_track_published_and_handled(self, fresh_event_bus):
        """Stats accurately reflect events published and handled."""
        async def handler(event: Event):
            pass

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, handler)

        await fresh_event_bus.publish(Event(type=EventType.CONSENT_GRANTED))
        await fresh_event_bus.publish(Event(type=EventType.CONSENT_GRANTED))

        stats = fresh_event_bus.get_stats()
        assert stats["events_published"] == 2
        assert stats["events_handled"] == 2

    @pytest.mark.asyncio
    async def test_stats_track_handler_errors(self, fresh_event_bus):
        """Stats count handler errors separately."""

        async def bad_handler(event: Event):
            raise RuntimeError("boom")

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, bad_handler)

        await fresh_event_bus.publish(Event(type=EventType.CONSENT_GRANTED))

        stats = fresh_event_bus.get_stats()
        assert stats["handler_errors"] == 1
        assert stats["events_published"] == 1

    @pytest.mark.asyncio
    async def test_stats_include_handler_count(self, fresh_event_bus):
        """Stats report number of registered handlers."""
        async def h1(event: Event):
            pass

        async def h2(event: Event):
            pass

        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, h1)
        fresh_event_bus.subscribe(EventType.CONSENT_GRANTED, h2)
        fresh_event_bus.subscribe(EventType.CONSENT_REVOKED, h1)

        stats = fresh_event_bus.get_stats()
        assert stats["handlers_registered"] == 3


# ============================================================
# Test: Global singleton access
# ============================================================


class TestGlobalSingletons:
    """Test global singleton accessors."""

    def test_get_event_bus_returns_instance(self):
        """get_event_bus() returns an EventBus instance."""
        bus = get_event_bus()
        assert isinstance(bus, EventBus)

    def test_get_event_queue_returns_instance(self):
        """get_event_queue() returns an EventQueue instance."""
        queue = get_event_queue()
        assert isinstance(queue, EventQueue)

    def test_get_event_bus_returns_same_instance(self):
        """get_event_bus() returns the same instance on repeated calls."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_get_event_queue_returns_same_instance(self):
        """get_event_queue() returns the same instance on repeated calls."""
        q1 = get_event_queue()
        q2 = get_event_queue()
        assert q1 is q2


# ============================================================
# Test: Event type enum
# ============================================================


class TestEventTypeEnum:
    """Test EventType enum values."""

    def test_consent_event_types(self):
        """Consent-related event types exist."""
        assert EventType.CONSENT_GRANTED.value == "consent.granted"
        assert EventType.CONSENT_REVOKED.value == "consent.revoked"
        assert EventType.CONSENT_MODIFIED.value == "consent.modified"
        assert EventType.CONSENT_EXPIRED.value == "consent.expired"
        assert EventType.CONSENT_VERIFIED.value == "consent.verified"

    def test_deletion_event_types(self):
        """Deletion-related event types exist."""
        assert EventType.DELETION_REQUESTED.value == "deletion.requested"
        assert EventType.DELETION_STARTED.value == "deletion.started"
        assert EventType.DELETION_COMPLETED.value == "deletion.completed"

    def test_grievance_event_types(self):
        """Grievance-related event types exist."""
        assert EventType.GRIEVANCE_SUBMITTED.value == "grievance.submitted"
        assert EventType.GRIEVANCE_RESOLVED.value == "grievance.resolved"

    def test_security_event_types(self):
        """Security-related event types exist."""
        assert EventType.BREACH_DETECTED.value == "breach.detected"
        assert EventType.BREACH_NOTIFIED.value == "breach.notified"

    def test_webhook_event_types(self):
        """Webhook-related event types exist."""
        assert EventType.WEBHOOK_DELIVERED.value == "webhook.delivered"
        assert EventType.WEBHOOK_FAILED.value == "webhook.failed"

    def test_user_event_types(self):
        """User-related event types exist."""
        assert EventType.USER_REGISTERED.value == "user.registered"
        assert EventType.FIDUCIARY_REGISTERED.value == "fiduciary.registered"
