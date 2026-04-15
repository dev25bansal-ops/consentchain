"""Cache key generation and cache service for consent queries.

Provides typed cache keys and a service layer for caching
with Redis (with in-memory fallback when Redis is unavailable).
"""

import json
import time
from typing import Any, Optional
from uuid import UUID


class CacheKey:
    """Generate typed cache keys for consent operations."""

    PREFIX = "consentchain"

    @classmethod
    def consent(cls, consent_id: str) -> str:
        return f"{cls.PREFIX}:consent:{consent_id}"

    @classmethod
    def consent_verification(cls, consent_id: UUID) -> str:
        return f"{cls.PREFIX}:consent:verify:{consent_id}"

    @classmethod
    def fiduciary(cls, fiduciary_id: str) -> str:
        return f"{cls.PREFIX}:fiduciary:{fiduciary_id}"

    @classmethod
    def fiduciary_consents(
        cls,
        fiduciary_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> str:
        return f"{cls.PREFIX}:consent:fiduciary:{fiduciary_id}:p{page}:l{limit}:s{status or 'all'}"

    @classmethod
    def principal(cls, principal_id: str) -> str:
        return f"{cls.PREFIX}:principal:{principal_id}"

    @classmethod
    def principal_consents(
        cls,
        principal_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> str:
        return f"{cls.PREFIX}:consent:principal:{principal_id}:p{page}:l{limit}:s{status or 'all'}"


class CacheService:
    """Cache service using Redis with in-memory fallback."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry)

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value by key."""
        # Try Redis first
        if self._redis:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception:
                pass

        # Fallback to in-memory cache
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._memory_cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Cache a value with the given TTL in seconds."""
        # Try Redis first
        if self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception:
                pass

        # Fallback to in-memory cache
        self._memory_cache[key] = (value, time.time() + ttl)

    async def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass

        self._memory_cache.pop(key, None)

    async def invalidate_pattern(self, pattern: str) -> None:
        """Remove all keys matching a glob pattern (Redis only)."""
        if self._redis:
            try:
                keys = await self._redis.keys(pattern)
                if keys:
                    await self._redis.delete(*keys)
            except Exception:
                pass

        # Clear matching in-memory keys
        import fnmatch
        to_delete = [k for k in self._memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in to_delete:
            del self._memory_cache[k]

    async def delete(self, key: str) -> None:
        """Alias for invalidate - remove a specific key from cache."""
        await self.invalidate(key)

    def get_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "memory_cache_size": len(self._memory_cache),
            "redis_connected": self._redis is not None,
        }


# Module-level instance (lazily initialized)
_cache_service: Optional[CacheService] = None


def get_cache_service(redis_client=None) -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(redis_client)
    elif redis_client and _cache_service._redis is None:
        # Upgrade from memory-only to Redis-backed
        _cache_service._redis = redis_client
    return _cache_service
