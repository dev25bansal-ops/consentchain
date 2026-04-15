from datetime import datetime, timedelta
from typing import Optional, Callable
from functools import wraps
import hashlib
import os
import logging

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis.asyncio as redis

logger = logging.getLogger(__name__)


def get_api_key_or_ip(request: Request) -> str:
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace(
        "Bearer ", ""
    )
    if api_key:
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return get_remote_address(request)


def get_fiduciary_id(request: Request) -> str:
    fiduciary_id = getattr(request.state, "fiduciary_id", None)
    if fiduciary_id:
        return str(fiduciary_id)
    return get_api_key_or_ip(request)


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")


def _test_redis_connection(url: str) -> bool:
    try:
        import asyncio

        async def test():
            client = redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
            await client.ping()
            await client.close()
            return True

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(test())
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"Redis connection test failed: {e}. Using in-memory rate limiting.")
        return False


STORAGE_URI = REDIS_URL if _test_redis_connection(REDIS_URL) else "memory://"

limiter = Limiter(
    key_func=get_api_key_or_ip,
    default_limits=["200/minute"],
    storage_uri=STORAGE_URI,
)

fiduciary_limiter = Limiter(
    key_func=get_fiduciary_id,
    default_limits=["1000/minute"],
    storage_uri=STORAGE_URI,
)


RATE_LIMITS = {
    "consent_create": "100/minute",
    "consent_verify": "1000/minute",
    "consent_query": "500/minute",
    "consent_revoke": "50/minute",
    "audit_query": "100/minute",
    "batch_create": "10/minute",
    "fiduciary_register": "5/hour",
}


def setup_rate_limiting(app):
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": exc.detail,
            },
        )

    return limiter


class TieredRateLimiter:
    TIERS = {
        "free": {
            "consent_create": "50/minute",
            "consent_verify": "100/minute",
            "consent_query": "100/minute",
        },
        "basic": {
            "consent_create": "200/minute",
            "consent_verify": "500/minute",
            "consent_query": "300/minute",
        },
        "enterprise": {
            "consent_create": "1000/minute",
            "consent_verify": "2000/minute",
            "consent_query": "1000/minute",
        },
    }

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get_tier(self, fiduciary_id: str) -> str:
        tier = await self.redis.get(f"tier:{fiduciary_id}")
        return tier.decode() if tier else "free"

    async def set_tier(self, fiduciary_id: str, tier: str) -> None:
        await self.redis.set(f"tier:{fiduciary_id}", tier)

    def get_limit_for_endpoint(self, tier: str, endpoint: str) -> str:
        tier_limits = self.TIERS.get(tier, self.TIERS["free"])
        return tier_limits.get(endpoint, "100/minute")

    async def check_rate_limit(
        self,
        fiduciary_id: str,
        endpoint: str,
        cost: int = 1,
    ) -> tuple[bool, dict]:
        tier = await self.get_tier(fiduciary_id)
        limit_str = self.get_limit_for_endpoint(tier, endpoint)

        limit_parts = limit_str.split("/")
        limit = int(limit_parts[0])
        window = limit_parts[1] if len(limit_parts) > 1 else "minute"

        window_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }.get(window, 60)

        key = f"ratelimit:{fiduciary_id}:{endpoint}"
        current = await self.redis.incrby(key, cost)

        if current == cost:
            await self.redis.expire(key, window_seconds)

        ttl = await self.redis.ttl(key)

        return (
            current <= limit,
            {
                "limit": limit,
                "remaining": max(0, limit - current),
                "reset": ttl,
                "tier": tier,
            },
        )


def rate_limit(endpoint: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            limit = RATE_LIMITS.get(endpoint, "100/minute")
            limiter.limit(limit)(func)
            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator
