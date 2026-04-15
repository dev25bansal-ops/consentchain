# ADR-007: Event-Driven Architecture with Event Bus

## Status
Accepted

## Date
2026-04-05

## Context
As ConsentChain evolved from a simple consent management API into a multi-tenant SaaS platform with GDPR compliance, billing, analytics, webhooks, AI features, and blockchain integration, the tightly coupled synchronous architecture became a bottleneck:

1. **Consent operations** — Creating a consent record now triggers: blockchain anchoring, audit logging, webhook notifications, analytics events, email notifications, and compliance checks. Doing all of this synchronously made API responses slow (>2s).
2. **Billing events** — Subscription changes need to propagate to rate limiting, feature flags, and tenant status without blocking the Stripe webhook response.
3. **Data subject requests** — GDPR erasure requests require coordination across PostgreSQL, Redis, IPFS, and blockchain, which can take seconds to minutes.
4. **Audit trail integrity** — Events must be durably recorded even if downstream consumers are temporarily unavailable.
5. **Future extensibility** — New features (AI anomaly detection, automated compliance reporting, regulator alerts) should be addable without modifying existing code.

**Alternatives considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **Synchronous function calls** | Simple, easy to debug, transactional consistency | Slow responses, cascading failures, tight coupling, hard to add new consumers |
| **Celery task queue** | Mature, Redis/RabbitMQ support, retry logic, scheduling | Heavy infrastructure (Celery beat + worker processes), Python-only consumers |
| **RabbitMQ** | Mature, reliable, complex routing, dead letter queues | Additional infrastructure to manage, AMQL protocol learning curve |
| **Kafka** | Extremely scalable, durable, consumer groups, replay | Heavy operational burden, overkill for our scale, ZooKeeper dependency |
| **In-memory Event Bus + Redis persistence** | Lightweight, low latency, simple deployment, Redis already in stack | Limited durability guarantees, single-process bus (mitigated with Redis queue) |

## Decision
Implement a **lightweight in-memory Event Bus with Redis-backed Event Queue** for durable event processing, using an in-process pub/sub pattern for immediate fan-out and Redis Streams for durable, replayable event storage.

### Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Event Publishers                            │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │ Consent Svc │ │ Billing  │ │ Deletion  │ │ Auth Service     │  │
│  │             │ │ Service  │ │ Service   │ │                  │  │
│  │ publish()   │ │ publish()│ │ publish() │ │ publish()        │  │
│  └──────┬──────┘ └────┬─────┘ └─────┬─────┘ └────────┬─────────┘  │
│         │              │             │                 │             │
│         └──────────────┴──────┬──────┴─────────────────┘             │
│                               │                                       │
│                    ┌──────────▼──────────┐                            │
│                    │     EventBus         │  (in-memory pub/sub)      │
│                    │                      │                            │
│                    │  subscribe(handler)  │                            │
│                    │  publish(event)      │                            │
│                    └──────────┬──────────┘                            │
│                               │                                       │
│                    ┌──────────▼──────────┐                            │
│                    │     EventQueue       │  (Redis-backed durable)   │
│                    │                      │                            │
│                    │  enqueue(event)      │                            │
│                    │  dequeue()           │                            │
│                    │  replay(from_ts)     │                            │
│                    │  dead_letter_queue   │                            │
│                    └──────────┬──────────┘                            │
│                               │                                       │
├───────────────────────────────┼───────────────────────────────────────┤
│                        Event Consumers                                │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐     │
│  │ Audit Logger│ │ Webhook  │ │ Analytics │ │ Compliance       │     │
│  │             │ │ Dispatcher│ │ Engine    │ │ Monitor          │     │
│  │ consume()   │ │ consume()│ │ consume() │ │ consume()        │     │
│  └─────────────┘ └──────────┘ └───────────┘ └──────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
```

### Event Types

```python
class EventType(Enum):
    # Consent lifecycle
    CONSENT_GRANTED = "consent.granted"
    CONSENT_REVOKED = "consent.revoked"
    CONSENT_MODIFIED = "consent.modified"
    CONSENT_EXPIRED = "consent.expired"

    # Data subject rights
    DATA_SUBJECT_REQUEST = "dsr.submitted"
    DATA_SUBJECT_COMPLETED = "dsr.completed"
    DATA_SUBJECT_ERASURE = "dsr.erasure_executed"

    # Billing
    BILLING_SUBSCRIPTION_CREATED = "billing.subscription.created"
    BILLING_SUBSCRIPTION_CANCELLED = "billing.subscription.cancelled"
    BILLING_PAYMENT_FAILED = "billing.payment.failed"
    BILLING_INVOICE_PAID = "billing.invoice.paid"

    # Security
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    CONSENT_ANOMALY = "consent.anomaly_detected"

    # System
    TENANT_CREATED = "tenant.created"
    TENANT_SUSPENDED = "tenant.suspended"
    TENANT_REACTIVATED = "tenant.reactivated"
```

### Implementation

- `api.events.Event` — Dataclass with `id`, `type`, `data`, `source`, `timestamp`, `version`
- `api.events.EventBus` — In-memory pub/sub with handler registration via `@on_event` decorator
- `api.events.EventQueue` — Redis-backed queue with enqueue, dequeue, replay, and dead letter queue
- `api.events.publish_event()` — Convenience function to publish to both bus and queue
- `api.events.get_event_bus()` / `get_event_queue()` — Singleton accessors
- Event serialization to JSON for Redis persistence
- Priority event support (high-priority events processed first)
- Dead letter queue for failed event processing (retries up to 3 times)

### Redis Data Structures

| Structure | Purpose |
|---|---|
| `event:queue` | Redis list for FIFO event queue |
| `event:stream` | Redis Stream for durable event log with replay capability |
| `event:dlq` | Redis list for dead letter queue (failed events) |
| `event:processed:{id}` | Redis key for deduplication (TTL: 24h) |

## Consequences

### Positive
- **Decoupled services** — New consumers can subscribe without modifying publishers
- **Improved response times** — Non-critical operations (analytics, webhooks) happen asynchronously
- **Durable event log** — Redis Streams enable replay for debugging and reprocessing
- **Dead letter queue** — Failed events are preserved for manual inspection and retry
- **Lightweight** — No additional infrastructure beyond Redis (already in stack)
- **Testable** — Event handlers can be unit-tested in isolation
- **Extensible** — Adding a new consumer is a single `@on_event` decorator

### Negative
- **Eventual consistency** — Downstream systems may briefly be out of sync (mitigated by queue ordering)
- **Debugging complexity** — Asynchronous flows are harder to trace than synchronous calls
- **Redis as single point of failure** — If Redis goes down, events are lost until recovery (mitigated by in-memory fallback)
- **No cross-process pub/sub** — In-memory EventBus doesn't fan out across multiple API instances (Redis queue handles this)
- **Event schema evolution** — Changing event data structures requires careful versioning
- **No guaranteed exactly-once processing** — Events may be processed multiple times on retry (handlers must be idempotent)

## Migration Path
If we outgrow the lightweight event bus:

1. Replace `EventQueue` backend with Kafka or RabbitMQ adapter
2. Keep `EventBus` interface unchanged — only backend implementation changes
3. Add consumer group support for parallel processing
4. Implement schema registry for event versioning (e.g., Apache Avro, Protobuf)
5. Add distributed tracing (OpenTelemetry) for cross-service event correlation

## References
- [Enterprise Integration Patterns — Message Bus](https://www.enterpriseintegrationpatterns.com/patterns/messaging/MessageBus.html)
- [Redis Streams Documentation](https://redis.io/docs/data-types/streams/)
- [Event-Driven Architecture (Martin Fowler)](https://martinfowler.com/articles/201701-event-driven.html)
- [Dead Letter Queue Pattern](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
