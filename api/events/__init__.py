"""Event-Driven Architecture for ConsentChain.

Provides:
- Event bus for pub/sub messaging
- Event queue for async processing
- Event handlers with retry logic
"""

from typing import Dict, List, Callable, Any, Optional, Set, Awaitable
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    CONSENT_GRANTED = "consent.granted"
    CONSENT_REVOKED = "consent.revoked"
    CONSENT_MODIFIED = "consent.modified"
    CONSENT_EXPIRED = "consent.expired"
    CONSENT_VERIFIED = "consent.verified"

    DELETION_REQUESTED = "deletion.requested"
    DELETION_STARTED = "deletion.started"
    DELETION_COMPLETED = "deletion.completed"

    BREACH_DETECTED = "breach.detected"
    BREACH_NOTIFIED = "breach.notified"

    GRIEVANCE_SUBMITTED = "grievance.submitted"
    GRIEVANCE_RESOLVED = "grievance.resolved"

    WEBHOOK_DELIVERED = "webhook.delivered"
    WEBHOOK_FAILED = "webhook.failed"

    USER_REGISTERED = "user.registered"
    FIDUCIARY_REGISTERED = "fiduciary.registered"


@dataclass
class Event:
    id: UUID = field(default_factory=uuid4)
    type: EventType = EventType.CONSENT_GRANTED
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "consentchain-api"
    version: str = "1.0"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "data": self.data,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=UUID(data["id"]),
            type=EventType(data["type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "consentchain-api"),
            version=data.get("version", "1.0"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    In-memory event bus for pub/sub messaging.

    Usage:
        bus = EventBus()

        # Subscribe to events
        async def handle_consent(event: Event):
            print(f"Consent event: {event.data}")

        bus.subscribe(EventType.CONSENT_GRANTED, handle_consent)

        # Publish events
        await bus.publish(Event(
            type=EventType.CONSENT_GRANTED,
            data={"consent_id": "123", "principal_id": "user-1"},
        ))
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._middleware: List[Callable[[Event], Awaitable[Event]]] = []
        self._lock = asyncio.Lock()
        self._stats = {
            "events_published": 0,
            "events_handled": 0,
            "handler_errors": 0,
        }

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ):
        """Subscribe to a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")

    def subscribe_all(self, handler: EventHandler):
        """Subscribe to all events."""
        self._wildcard_handlers.append(handler)
        logger.debug("Subscribed wildcard handler")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ):
        """Unsubscribe from a specific event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def add_middleware(self, middleware: Callable[[Event], Awaitable[Event]]):
        """Add middleware that processes events before handlers."""
        self._middleware.append(middleware)

    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self._stats["events_published"] += 1

        processed_event = event
        for middleware in self._middleware:
            try:
                processed_event = await middleware(processed_event)
            except Exception as e:
                logger.error(f"Middleware error: {e}")

        handlers = list(self._handlers.get(event.type, []))
        handlers.extend(self._wildcard_handlers)

        if not handlers:
            logger.debug(f"No handlers for event type: {event.type.value}")
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call_handler(handler, processed_event))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self._stats["handler_errors"] += 1
            else:
                self._stats["events_handled"] += 1

    async def _safe_call_handler(
        self,
        handler: EventHandler,
        event: Event,
    ):
        """Call handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Handler error for {event.type.value}: {e}",
                exc_info=True,
            )
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "handlers_registered": sum(len(handlers) for handlers in self._handlers.values()),
            "wildcard_handlers": len(self._wildcard_handlers),
            "event_types_subscribed": list(self._handlers.keys()),
        }


class EventQueue:
    """
    Persistent event queue for async processing.

    Events are queued and processed by background workers.
    Supports priority queuing and delayed processing.
    """

    def __init__(self, max_size: int = 10000):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._pending: Dict[UUID, Event] = {}
        self._stats = {
            "queued": 0,
            "processed": 0,
            "failed": 0,
        }

    async def enqueue(
        self,
        event: Event,
        priority: int = 0,
        delay_seconds: float = 0,
    ):
        """Add event to queue with optional priority and delay."""
        process_at = datetime.now(timezone.utc).timestamp() + delay_seconds
        await self._queue.put((priority, process_at, event))
        self._pending[event.id] = event
        self._stats["queued"] += 1
        logger.debug(f"Queued event: {event.type.value} (priority={priority})")

    async def dequeue(self, timeout: float = 1.0) -> Optional[Event]:
        """Get next event from queue."""
        try:
            priority, process_at, event = await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout,
            )

            now = datetime.now(timezone.utc).timestamp()
            if process_at > now:
                await self._queue.put((priority, process_at, event))
                return None

            self._pending.pop(event.id, None)
            return event

        except asyncio.TimeoutError:
            return None

    async def ack(self, event_id: UUID):
        """Acknowledge successful processing."""
        self._pending.pop(event_id, None)
        self._stats["processed"] += 1

    async def nack(self, event_id: UUID, requeue: bool = True):
        """Negative acknowledgement - event processing failed."""
        event = self._pending.get(event_id)
        if event and requeue:
            await self.enqueue(event)
        self._stats["failed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "pending": len(self._pending),
        }


_event_bus: Optional[EventBus] = None
_event_queue: Optional[EventQueue] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_event_queue() -> EventQueue:
    """Get or create the global event queue."""
    global _event_queue
    if _event_queue is None:
        _event_queue = EventQueue()
    return _event_queue


async def publish_event(event_type: EventType, data: Dict[str, Any], **kwargs):
    """Convenience function to publish an event."""
    event = Event(type=event_type, data=data, **kwargs)
    await get_event_bus().publish(event)


def on_event(event_type: EventType):
    """Decorator to subscribe a function to an event type."""

    def decorator(func: EventHandler) -> EventHandler:
        get_event_bus().subscribe(event_type, func)
        return func

    return decorator
