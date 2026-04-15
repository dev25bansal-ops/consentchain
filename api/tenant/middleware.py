"""Tenant Context Middleware.

Provides request-level tenant context extraction for multi-tenant SaaS.
Supports multiple tenant identification methods:
- X-Tenant-ID header (explicit)
- Subdomain-based tenant resolution
- API key to tenant mapping
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, Callable
from uuid import UUID
import logging
import re
import json

from api.database import TenantDB, TenantStatusDB, DataFiduciaryDB
from api.tenant import TenantPlan, PLAN_LIMITS
from core.crypto import CryptoUtils

logger = logging.getLogger(__name__)


class TenantContext:
    """Thread-local tenant context for request handling."""

    _current_tenant: Optional[TenantDB] = None
    _tenant_id: Optional[UUID] = None
    _limits: dict = {}
    _features: list = []

    @classmethod
    def set_tenant(cls, tenant: TenantDB):
        cls._current_tenant = tenant
        cls._tenant_id = tenant.id
        plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan.value), PLAN_LIMITS[TenantPlan.FREE])
        cls._limits = plan_limits
        cls._features = plan_limits.get("features", [])

    @classmethod
    def get_tenant(cls) -> Optional[TenantDB]:
        return cls._current_tenant

    @classmethod
    def get_tenant_id(cls) -> Optional[UUID]:
        return cls._tenant_id

    @classmethod
    def has_feature(cls, feature: str) -> bool:
        if "*" in cls._features:
            return True
        return feature in cls._features

    @classmethod
    def get_limit(cls, limit_name: str) -> int:
        return cls._limits.get(limit_name, 0)

    @classmethod
    def clear(cls):
        cls._current_tenant = None
        cls._tenant_id = None
        cls._limits = {}
        cls._features = []


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate tenant context from requests."""

    def __init__(
        self,
        app,
        tenant_header: str = "X-Tenant-ID",
        subdomain_pattern: Optional[str] = None,
        excluded_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.tenant_header = tenant_header
        self.subdomain_pattern = subdomain_pattern
        self.excluded_paths = excluded_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/tenant/plans",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        TenantContext.clear()

        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        tenant = await self._resolve_tenant(request)

        if tenant:
            if tenant.status == TenantStatusDB.SUSPENDED:
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "Tenant account suspended",
                        "data": None,
                    },
                )

            if tenant.status == TenantStatusDB.CANCELLED:
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "Tenant account cancelled",
                        "data": None,
                    },
                )

            TenantContext.set_tenant(tenant)
            request.state.tenant = tenant
            request.state.tenant_id = tenant.id

        response = await call_next(request)

        if tenant:
            response.headers["X-Tenant-ID"] = str(tenant.id)

        return response

    def _is_excluded_path(self, path: str) -> bool:
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    async def _resolve_tenant(self, request: Request) -> Optional[TenantDB]:
        tenant = await self._resolve_from_header(request)
        if tenant:
            return tenant

        tenant = await self._resolve_from_subdomain(request)
        if tenant:
            return tenant

        tenant = await self._resolve_from_api_key(request)
        if tenant:
            return tenant

        return None

    async def _resolve_from_header(self, request: Request) -> Optional[TenantDB]:
        tenant_id = request.headers.get(self.tenant_header)
        if not tenant_id:
            return None

        try:
            uuid = UUID(tenant_id)
        except ValueError:
            logger.warning(f"Invalid tenant ID format: {tenant_id}")
            return None

        session = getattr(request.state, "session", None)
        if not session:
            return None

        from sqlalchemy import select

        result = await session.execute(select(TenantDB).where(TenantDB.id == uuid))
        return result.scalar_one_or_none()

    async def _resolve_from_subdomain(self, request: Request) -> Optional[TenantDB]:
        host = request.headers.get("host", "")
        if not host:
            return None

        if self.subdomain_pattern:
            match = re.match(self.subdomain_pattern, host)
            if match:
                slug = match.group(1)
            else:
                return None
        else:
            parts = host.split(".")
            if len(parts) < 2:
                return None
            slug = parts[0]

        if slug in ("www", "api", "app", "admin", "dashboard"):
            return None

        session = getattr(request.state, "session", None)
        if not session:
            return None

        from sqlalchemy import select

        result = await session.execute(select(TenantDB).where(TenantDB.slug == slug))
        return result.scalar_one_or_none()

    async def _resolve_from_api_key(self, request: Request) -> Optional[TenantDB]:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        api_key = auth_header[7:]

        session = getattr(request.state, "session", None)
        if not session:
            return None

        from sqlalchemy import select

        api_key_hash = CryptoUtils.hash_api_key(api_key)

        result = await session.execute(
            select(DataFiduciaryDB).where(DataFiduciaryDB.api_key_hash == api_key_hash)
        )
        fiduciary = result.scalar_one_or_none()

        if not fiduciary:
            return None

        fiduciary_tenant_id = getattr(fiduciary, "tenant_id", None)
        if not fiduciary_tenant_id:
            return None

        result = await session.execute(select(TenantDB).where(TenantDB.id == fiduciary_tenant_id))
        return result.scalar_one_or_none()


def get_current_tenant() -> Optional[TenantDB]:
    """Get the current tenant from request context."""
    return TenantContext.get_tenant()


def get_current_tenant_id() -> Optional[UUID]:
    """Get the current tenant ID from request context."""
    return TenantContext.get_tenant_id()


def require_tenant() -> TenantDB:
    """Require a tenant in context, raise exception if not found."""
    tenant = get_current_tenant()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant context required")
    return tenant


def require_feature(feature: str):
    """Decorator to require a feature for an endpoint."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            tenant = get_current_tenant()
            if tenant and not TenantContext.has_feature(feature):
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature}' not available on {tenant.plan.value} plan",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_quota(resource_type: str):
    """Decorator to check quota before operation."""

    def decorator(func):
        async def wrapper(*args, request: Request = None, **kwargs):
            from api.tenant import tenant_service
            from uuid import UUID

            tenant = get_current_tenant()
            if tenant:
                quota = tenant_service.check_quota(tenant.id, resource_type)
                if not quota.get("allowed", True):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Quota exceeded for {resource_type}",
                    )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class TenantQuotaExceeded(Exception):
    """Exception raised when tenant quota is exceeded."""

    def __init__(self, resource_type: str, current: int, limit: int):
        self.resource_type = resource_type
        self.current = current
        self.limit = limit
        self.message = f"Quota exceeded for {resource_type}: {current}/{limit}"
        super().__init__(self.message)


class FeatureNotAvailable(Exception):
    """Exception raised when feature is not available for tenant plan."""

    def __init__(self, feature: str, plan: str):
        self.feature = feature
        self.plan = plan
        self.message = f"Feature '{feature}' not available on {plan} plan"
        super().__init__(self.message)
