"""Request ID Middleware - Unique request tracing for debugging and logging."""

import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to every request for tracing.

    Request IDs can be used to:
    - Trace requests through logs
    - Correlate errors with specific requests
    - Debug issues in production

    The request ID is:
    1. Extracted from X-Request-ID header if present
    2. Generated as a new UUID if not present
    3. Added to response headers as X-Request-ID
    4. Added to request.state for access in handlers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        logger.debug(f"Request {request_id}: {request.method} {request.url.path}")

        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Add rate limit headers to responses.

    Headers added:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Seconds until window resets
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Add request timing to responses and logs.

    Headers added:
    - X-Response-Time: Time taken to process request in milliseconds
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import time

        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

        if elapsed_ms > 1000:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {elapsed_ms:.2f}ms"
            )

        return response
