"""Shared dependencies for authentication and session management."""

import json
import os
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import DataFiduciaryDB, DataPrincipalDB
from core.crypto import CryptoUtils

logger = logging.getLogger(__name__)
security = HTTPBearer()

TESTING = os.getenv("TESTING", "").lower() in ("1", "true", "yes")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


async def get_session():
    """Get async database session."""
    from api.main import async_session

    async with async_session() as session:
        yield session


async def get_redis_client():
    """Get Redis client."""
    from api.main import redis_client

    return redis_client


async def verify_fiduciary_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Verify fiduciary API key and return fiduciary data.

    Uses Redis caching for performance.
    This is the SINGLE SOURCE OF TRUTH for fiduciary authentication.
    """
    redis_client = await get_redis_client()

    api_key = credentials.credentials
    api_key_hash = CryptoUtils.hash_api_key(api_key)
    cache_key = f"fiduciary:{api_key_hash}"

    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    result = await session.execute(
        select(DataFiduciaryDB).where(DataFiduciaryDB.api_key_hash == api_key_hash)
    )
    fiduciary = result.scalar_one_or_none()

    if not fiduciary:
        raise HTTPException(status_code=401, detail="Invalid API key")

    fiduciary_data = {
        "fiduciary_id": str(fiduciary.id),
        "name": fiduciary.name,
        "wallet_address": fiduciary.wallet_address,
        "tier": getattr(fiduciary, 'tier', 'unknown'),
    }

    if redis_client:
        try:
            await redis_client.setex(cache_key, 300, json.dumps(fiduciary_data))
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    return fiduciary_data


async def verify_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify user JWT token and return payload.

    Checks the token blacklist to ensure revoked tokens are rejected.

    Raises:
        HTTPException: If token is invalid, expired, or revoked.
    """
    import jwt
    import hashlib
    from sqlalchemy import select
    from api.database import TokenBlacklistDB

    jwt_secret = os.getenv("JWT_SECRET")

    if not jwt_secret:
        logger.error("JWT_SECRET not set in environment")
        raise HTTPException(
            status_code=500, detail="Server configuration error: JWT_SECRET not configured"
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

        if payload.get("type") not in ("access", "refresh"):
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Check if token has been blacklisted (revoked)
        jti = payload.get("jti")
        if jti:
            from api.main import async_session
            from datetime import datetime, timezone

            async with async_session() as session:
                blacklist_result = await session.execute(
                    select(TokenBlacklistDB).where(
                        TokenBlacklistDB.jti == jti,
                        TokenBlacklistDB.expires_at > datetime.now(timezone.utc),
                    )
                )
                if blacklist_result.scalar_one_or_none():
                    raise HTTPException(status_code=401, detail="Token has been revoked")

        return payload
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token attempt: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_principal_ownership(
    principal_id: UUID,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Verify that the authenticated user owns the specified principal account.

    Returns user payload if authorized.
    """
    user_principal_id = user.get("sub")

    if str(principal_id) != user_principal_id:
        result = await session.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.id == principal_id)
        )
        principal = result.scalar_one_or_none()

        if not principal or principal.wallet_address != user.get("wallet_address"):
            raise HTTPException(status_code=403, detail="Access denied")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Get user from JWT token if provided, otherwise return None.
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None

    try:
        return await verify_user_jwt(credentials)
    except HTTPException:
        return None


class RateLimitDep:
    """Dependency for rate limiting configuration."""

    DEFAULT_LIMITS = {
        "consent_create": "100/minute",
        "consent_verify": "1000/minute",
        "consent_query": "500/minute",
        "consent_revoke": "50/minute",
        "audit_query": "100/minute",
        "batch_create": "10/minute",
        "fiduciary_register": "5/hour",
        "public_consent": "10/minute",
        "public_grievance": "5/minute",
        "grievance_submit": "20/minute",
        "children_verify": "10/minute",
    }

    @classmethod
    def get_limit(cls, endpoint: str) -> str:
        return cls.DEFAULT_LIMITS.get(endpoint, "100/minute")


def validate_wallet_address(wallet: str) -> bool:
    """Validate Algorand wallet address format."""
    import re

    return bool(re.match(r"^[A-Z2-7]{58}$", wallet))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    try:
        UUID(uuid_str)
        return True
    except (ValueError, TypeError):
        return False
