from typing import Optional
from uuid import UUID
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from api.database import DataFiduciaryDB
from core.crypto import CryptoUtils


_tenant_context: ContextVar[Optional["TenantContext"]] = ContextVar("tenant_context", default=None)


@dataclass
class TenantContext:
    fiduciary_id: UUID
    name: str
    wallet_address: str
    tier: str = "free"
    is_admin: bool = False


def get_tenant_context() -> Optional[TenantContext]:
    return _tenant_context.get()


def set_tenant_context(context: Optional[TenantContext]) -> None:
    _tenant_context.set(context)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/fiduciary/register",
    }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "")

            session = request.app.state.db_session_factory()
            async with session:
                tenant_context = await self._validate_api_key(session, api_key)
                if tenant_context:
                    request.state.tenant_context = tenant_context
                    request.state.fiduciary_id = tenant_context.fiduciary_id
                    set_tenant_context(tenant_context)

        response = await call_next(request)
        set_tenant_context(None)

        return response

    async def _validate_api_key(
        self,
        session: AsyncSession,
        api_key: str,
    ) -> Optional[TenantContext]:
        api_key_hash = CryptoUtils.hash_api_key(api_key)

        result = await session.execute(
            select(DataFiduciaryDB).where(DataFiduciaryDB.api_key_hash == api_key_hash)
        )
        fiduciary = result.scalar_one_or_none()

        if not fiduciary:
            return None

        return TenantContext(
            fiduciary_id=fiduciary.id,
            name=fiduciary.name,
            wallet_address=fiduciary.wallet_address,
        )


def require_tenant() -> TenantContext:
    context = get_tenant_context()
    if not context:
        raise HTTPException(
            status_code=401,
            detail="Tenant context required. Provide valid API key.",
        )
    return context


def tenant_filtered_query(model_class, query, tenant_field: str = "fiduciary_id"):
    context = get_tenant_context()
    if context and not context.is_admin:
        filter_column = getattr(model_class, tenant_field)
        query = query.where(filter_column == context.fiduciary_id)
    return query


class TenantRepository:
    def __init__(self, session: AsyncSession, model_class):
        self.session = session
        self.model_class = model_class
        self._tenant_id = None

    @property
    def tenant_id(self) -> Optional[UUID]:
        context = get_tenant_context()
        return context.fiduciary_id if context else self._tenant_id

    def set_tenant(self, tenant_id: UUID) -> None:
        self._tenant_id = tenant_id

    def _apply_tenant_filter(self, query, tenant_field: str = "fiduciary_id"):
        if self.tenant_id:
            filter_column = getattr(self.model_class, tenant_field)
            query = query.where(filter_column == self.tenant_id)
        return query

    async def get(self, id: UUID, tenant_field: str = "fiduciary_id"):
        query = select(self.model_class).where(self.model_class.id == id)
        query = self._apply_tenant_filter(query, tenant_field)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, filters: dict = None, tenant_field: str = "fiduciary_id"):
        query = select(self.model_class)
        query = self._apply_tenant_filter(query, tenant_field)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    query = query.where(getattr(self.model_class, key) == value)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, **kwargs):
        if self.tenant_id and "fiduciary_id" not in kwargs:
            kwargs["fiduciary_id"] = self.tenant_id

        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, id: UUID, **kwargs):
        instance = await self.get(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        return instance

    async def delete(self, id: UUID) -> bool:
        instance = await self.get(id)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True
