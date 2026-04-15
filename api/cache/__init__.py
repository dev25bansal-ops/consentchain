"""Caching Layer for ConsentChain using Redis.

Provides:
- Distributed caching for frequently accessed data
- Cache invalidation strategies
- TTL-based expiration
- Cache hit/miss metrics
"""

from typing import Optional, Any, Dict, List, Callable, TypeVar, Generic
from datetime import datetime, timezone, timedelta
from functools import wraps
import json
import hashlib
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar("T")

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


class CacheKey:
    """Utility class for generating cache keys."""

    PREFIX = "consentchain"

    @staticmethod
    def consent(consent_id: str) -> str:
        return f"{CacheKey.PREFIX}:consent:{consent_id}"

    @staticmethod
    def principal_consents(principal_id: str, page: int = 1) -> str:
        return f"{CacheKey.PREFIX}:principal:{principal_id}:consents:page:{page}"

    @staticmethod
    def fiduciary(fiduciary_id: str) -> str:
        return f"{CacheKey.PREFIX}:fiduciary:{fiduciary_id}"

    @staticmethod
    def fiduciary_consents(
        fiduciary_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> str:
        return f"{CacheKey.PREFIX}:consent:fiduciary:{fiduciary_id}:p{page}:l{limit}:s{status or 'all'}"

    @staticmethod
    def principal_consents(
        principal_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> str:
        return f"{CacheKey.PREFIX}:consent:principal:{principal_id}:p{page}:l{limit}:s{status or 'all'}"

    @staticmethod
    def consent_verification(consent_id: str) -> str:
        return f"{CacheKey.PREFIX}:verification:{consent_id}"

    @staticmethod
    def compliance_status(fiduciary_id: str) -> str:
        return f"{CacheKey.PREFIX}:compliance:{fiduciary_id}"

    @staticmethod
    def template(template_id: str, language: str) -> str:
        return f"{CacheKey.PREFIX}:template:{template_id}:{language}"

    @staticmethod
    def rate_limit(identifier: str) -> str:
        return f"{CacheKey.PREFIX}:ratelimit:{identifier}"


class CacheStats:
    """Cache statistics tracking."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate_percent": round(self.hit_rate, 2),
        }


class CacheService:
    """Redis-based caching service with fallback to in-memory cache."""

    DEFAULT_TTL = 300  # 5 minutes
    LONG_TTL = 3600  # 1 hour
    SHORT_TTL = 60  # 1 minute

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict[str, tuple[Any, float]] = {}
        self._connected = False
        self._stats = CacheStats()

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using local cache")
            self._connected = False
            return False

        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis: {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using local cache")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self._connected and self._redis:
                value = await self._redis.get(key)
                if value is not None:
                    self._stats.hits += 1
                    return json.loads(value)
            else:
                if key in self._local_cache:
                    value, expiry = self._local_cache[key]
                    if expiry > datetime.now(timezone.utc).timestamp():
                        self._stats.hits += 1
                        return value
                    else:
                        del self._local_cache[key]

            self._stats.misses += 1
            return None
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            if self._connected and self._redis:
                await self._redis.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str),
                )
            else:
                expiry = datetime.now(timezone.utc).timestamp() + ttl
                self._local_cache[key] = (value, expiry)

            self._stats.sets += 1
            return True
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self._connected and self._redis:
                await self._redis.delete(key)
            elif key in self._local_cache:
                del self._local_cache[key]

            self._stats.deletes += 1
            return True
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        deleted = 0
        try:
            if self._connected and self._redis:
                keys = await self._redis.keys(pattern)
                if keys:
                    deleted = await self._redis.delete(*keys)
            else:
                import fnmatch

                keys_to_delete = [k for k in self._local_cache if fnmatch.fnmatch(k, pattern)]
                for key in keys_to_delete:
                    del self._local_cache[key]
                    deleted += 1

            self._stats.deletes += deleted
            return deleted
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Cache delete_pattern error for {pattern}: {e}")
            return 0

    async def invalidate_consent(self, consent_id: str):
        """Invalidate all cache entries for a consent."""
        patterns = [
            f"{CacheKey.PREFIX}:consent:{consent_id}*",
            f"{CacheKey.PREFIX}:verification:{consent_id}*",
            f"{CacheKey.PREFIX}:principal:*:consents:*",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    async def invalidate_fiduciary(self, fiduciary_id: str):
        """Invalidate all cache entries for a fiduciary."""
        patterns = [
            f"{CacheKey.PREFIX}:fiduciary:{fiduciary_id}*",
            f"{CacheKey.PREFIX}:compliance:{fiduciary_id}*",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    async def invalidate_principal(self, principal_id: str):
        """Invalidate all cache entries for a principal."""
        patterns = [
            f"{CacheKey.PREFIX}:principal:{principal_id}*",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._stats.to_dict()
        stats["backend"] = "redis" if self._connected else "local"
        stats["local_cache_size"] = len(self._local_cache) if not self._connected else 0
        return stats

    async def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        health = {
            "status": "healthy" if self._connected else "degraded",
            "backend": "redis" if self._connected else "local",
            "stats": self.get_stats(),
        }

        if self._connected and self._redis:
            try:
                info = await self._redis.info()
                health["redis_version"] = info.get("redis_version")
                health["connected_clients"] = info.get("connected_clients")
                health["used_memory_human"] = info.get("used_memory_human")
            except Exception:
                health["status"] = "unhealthy"

        return health


def cached(
    key_prefix: str,
    ttl: int = CacheService.DEFAULT_TTL,
    key_builder: Optional[Callable] = None,
):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_service()

            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [key_prefix, str(args), str(sorted(kwargs.items()))]
                key_hash = hashlib.md5("".join(key_parts).encode()).hexdigest()
                cache_key = f"{CacheKey.PREFIX}:decorated:{key_prefix}:{key_hash}"

            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)

            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def init_cache() -> CacheService:
    """Initialize and connect the cache service."""
    cache = get_cache_service()
    await cache.connect()
    return cache


async def shutdown_cache():
    """Shutdown the cache service."""
    global _cache_service
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
