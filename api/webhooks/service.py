import hashlib
import hmac
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from enum import Enum
import httpx
from pydantic import BaseModel, Field
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class WebhookStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRY = "RETRY"


class WebhookSubscription(BaseModel):
    id: UUID
    fiduciary_id: UUID
    callback_url: str
    secret: str
    events: List[str]
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookDelivery(BaseModel):
    id: UUID
    subscription_id: UUID
    event_type: str
    payload: Dict[str, Any]
    status: WebhookStatus = WebhookStatus.PENDING
    attempts: int = 0
    max_attempts: int = 5
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookService:
    MAX_RETRIES = 5
    RETRY_DELAYS = [1, 5, 15, 60, 300]
    DEAD_LETTER_STREAM = "webhooks:dead_letter"
    WEBHOOK_STREAM = "webhooks:pending"

    def __init__(
        self,
        redis_client: redis.Redis,
        db: Optional[AsyncSession] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.redis = redis_client
        self.db = db
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)

    def generate_signature(self, secret: str, payload: str, timestamp: str) -> str:
        message = f"{timestamp}.{payload}"
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return f"sha256={signature}"

    async def queue_webhook(
        self,
        subscription_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
    ) -> UUID:
        delivery_id = uuid4()
        delivery = WebhookDelivery(
            id=delivery_id,
            subscription_id=subscription_id,
            event_type=event_type,
            payload=payload,
        )

        if self.db:
            from api.database import WebhookDeliveryDB, WebhookStatusDB

            db_delivery = WebhookDeliveryDB(
                id=delivery_id,
                subscription_id=subscription_id,
                event_type=event_type,
                payload=json.dumps(payload),
                status=WebhookStatusDB.PENDING,
                attempts=0,
            )
            self.db.add(db_delivery)
            await self.db.commit()

        await self.redis.xadd(
            self.WEBHOOK_STREAM,
            {
                "delivery_id": str(delivery_id),
                "subscription_id": str(subscription_id),
                "event_type": event_type,
                "payload": json.dumps(payload),
                "attempts": "0",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return delivery_id

    async def _update_delivery_status(
        self,
        delivery_id: UUID,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        if self.db:
            from api.database import WebhookDeliveryDB, WebhookStatusDB

            result = await self.db.execute(
                select(WebhookDeliveryDB).where(WebhookDeliveryDB.id == delivery_id)
            )
            db_delivery = result.scalar_one_or_none()
            if db_delivery:
                db_delivery.status = WebhookStatusDB[status]
                db_delivery.last_error = error
                db_delivery.last_attempt_at = datetime.now(timezone.utc)
                if status == "DELIVERED":
                    db_delivery.delivered_at = datetime.now(timezone.utc)
                db_delivery.attempts += 1
                await self.db.commit()

    async def deliver_webhook(
        self,
        subscription: WebhookSubscription,
        delivery: WebhookDelivery,
    ) -> bool:
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        payload_str = json.dumps(delivery.payload)
        signature = self.generate_signature(subscription.secret, payload_str, timestamp)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery-ID": str(delivery.id),
        }

        try:
            response = await self.http_client.post(
                subscription.callback_url,
                content=payload_str,
                headers=headers,
            )

            if response.status_code >= 200 and response.status_code < 300:
                return True
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            delivery.last_error = str(e)
            delivery.attempts += 1
            delivery.last_attempt_at = datetime.now(timezone.utc)

            if delivery.attempts >= self.MAX_RETRIES:
                await self._move_to_dead_letter(subscription, delivery)
            else:
                delay = self.RETRY_DELAYS[min(delivery.attempts - 1, len(self.RETRY_DELAYS) - 1)]
                await self._schedule_retry(subscription, delivery, delay)

            return False

    async def _move_to_dead_letter(
        self,
        subscription: WebhookSubscription,
        delivery: WebhookDelivery,
    ) -> None:
        await self.redis.xadd(
            self.DEAD_LETTER_STREAM,
            {
                "delivery_id": str(delivery.id),
                "subscription_id": str(subscription.id),
                "fiduciary_id": str(subscription.fiduciary_id),
                "event_type": delivery.event_type,
                "payload": json.dumps(delivery.payload),
                "attempts": str(delivery.attempts),
                "last_error": delivery.last_error or "",
                "created_at": delivery.created_at.isoformat(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _schedule_retry(
        self,
        subscription: WebhookSubscription,
        delivery: WebhookDelivery,
        delay_seconds: int,
    ) -> None:
        retry_stream = f"webhooks:retry:{delay_seconds}"
        await self.redis.xadd(
            retry_stream,
            {
                "delivery_id": str(delivery.id),
                "subscription_id": str(subscription.id),
                "event_type": delivery.event_type,
                "payload": json.dumps(delivery.payload),
                "attempts": str(delivery.attempts),
            },
        )

    async def process_pending_webhooks(self, batch_size: int = 10) -> int:
        messages = await self.redis.xread(
            {self.WEBHOOK_STREAM: "0"},
            count=batch_size,
        )

        processed = 0
        for stream, entries in messages:
            for entry_id, data in entries:
                delivery_id = UUID(data["delivery_id"])
                subscription_id = UUID(data["subscription_id"])

                await self.redis.xdel(self.WEBHOOK_STREAM, entry_id)
                processed += 1

        return processed

    async def get_dead_letter_count(self) -> int:
        info = await self.redis.xinfo_stream(self.DEAD_LETTER_STREAM)
        return info.get("length", 0)

    async def replay_dead_letter(self, delivery_id: UUID) -> bool:
        messages = await self.redis.xread(
            {self.DEAD_LETTER_STREAM: "0"},
        )

        for stream, entries in messages:
            for entry_id, data in entries:
                if UUID(data["delivery_id"]) == delivery_id:
                    await self.redis.xadd(
                        self.WEBHOOK_STREAM,
                        {
                            "delivery_id": data["delivery_id"],
                            "subscription_id": data["subscription_id"],
                            "event_type": data["event_type"],
                            "payload": data["payload"],
                            "attempts": "0",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    await self.redis.xdel(self.DEAD_LETTER_STREAM, entry_id)
                    return True

        return False

    async def close(self):
        await self.http_client.aclose()
