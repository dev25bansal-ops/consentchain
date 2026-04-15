import secrets
import os
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib
import time
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

TESTING = os.getenv("TESTING", "").lower() in ("1", "true", "yes")

CSRF_TOKEN_EXPIRY = 3600

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None
try:
    redis_client = redis.from_url(
        redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2
    )
except Exception as e:
    logger.warning(f"Failed to connect to Redis for CSRF: {e}. Using in-memory fallback.")
    redis_client = None

csrf_tokens: dict[str, tuple[str, float]] = {}


async def generate_csrf_token(session_id: str) -> str:
    token = secrets.token_urlsafe(32)

    if redis_client:
        try:
            await redis_client.setex(f"csrf:{session_id}", CSRF_TOKEN_EXPIRY, token)
        except Exception:
            csrf_tokens[session_id] = (token, time.time())
    else:
        csrf_tokens[session_id] = (token, time.time())

    return token


async def verify_csrf_token(session_id: str, token: str) -> bool:
    if redis_client:
        try:
            stored_token = await redis_client.get(f"csrf:{session_id}")
            if stored_token:
                return secrets.compare_digest(stored_token, token)
            return False
        except Exception:
            pass

    if session_id not in csrf_tokens:
        return False

    stored_token, created_at = csrf_tokens[session_id]

    if time.time() - created_at > CSRF_TOKEN_EXPIRY:
        del csrf_tokens[session_id]
        return False

    return secrets.compare_digest(stored_token, token)


async def cleanup_expired_tokens():
    if redis_client:
        return

    current_time = time.time()
    expired = [
        sid
        for sid, (_, created_at) in csrf_tokens.items()
        if current_time - created_at > CSRF_TOKEN_EXPIRY
    ]
    for sid in expired:
        del csrf_tokens[sid]


async def get_session_id(request: Request) -> str:
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = secrets.token_urlsafe(16)
    return session_id


async def verify_csrf(request: Request, session_id: str = Depends(get_session_id)):
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return True

    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    if not verify_csrf_token(session_id, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    return True


def get_csrf_token_endpoint(session_id: str = None) -> dict:
    import asyncio

    if session_id is None:
        session_id = secrets.token_urlsafe(16)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    token = loop.run_until_complete(generate_csrf_token(session_id))
    return {"csrf_token": token, "session_id": session_id, "expires_in": CSRF_TOKEN_EXPIRY}


class CSRFProtection:
    def __init__(self, exempt_methods: list[str] = None, exempt_paths: list[str] = None):
        self.exempt_methods = exempt_methods or ["GET", "HEAD", "OPTIONS"]
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def __call__(self, request: Request, call_next):
        if request.method in self.exempt_methods:
            return await call_next(request)

        for path in self.exempt_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        if request.url.path.startswith("/api/v1/public/"):
            return await call_next(request)

        csrf_token = request.headers.get("X-CSRF-Token")
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")

        if not csrf_token or not session_id:
            from fastapi.responses import JSONResponse

            if TESTING:
                logger.warning(
                    f"CSRF protection: token or session missing (TESTING mode - allowing request)"
                )
                return await call_next(request)

            return JSONResponse(
                status_code=403, content={"detail": "CSRF protection: token or session missing"}
            )

        if not verify_csrf_token(session_id, csrf_token):
            from fastapi.responses import JSONResponse

            if TESTING:
                logger.warning(
                    f"CSRF protection: invalid token (TESTING mode - allowing request)"
                )
                return await call_next(request)

            return JSONResponse(
                status_code=403, content={"detail": "CSRF protection: invalid token"}
            )

        return await call_next(request)
