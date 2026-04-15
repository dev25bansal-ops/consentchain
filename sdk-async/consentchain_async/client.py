"""Async client for ConsentChain API."""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID

import httpx
from pydantic import TypeAdapter

from .models import (
    ConsentRecord,
    ConsentCreate,
    ConsentUpdate,
    Fiduciary,
    DataPrincipal,
    WebhookSubscription,
    DashboardStats,
    WebhookDelivery,
)


class ConsentChainError(Exception):
    def __init__(self, message: str, status_code: int, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ConsentChainClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ConsentChainClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> Dict[str, Any]:
        client = await self._ensure_client()
        response = await client.request(method, path, **kwargs)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"detail": response.text}
            raise ConsentChainError(
                error_data.get("detail", "API Error"),
                response.status_code,
                error_data,
            )

        return response.json()

    @property
    def consents(self) -> "ConsentOperations":
        return ConsentOperations(self)

    @property
    def fiduciaries(self) -> "FiduciaryOperations":
        return FiduciaryOperations(self)

    @property
    def principals(self) -> "PrincipalOperations":
        return PrincipalOperations(self)

    @property
    def webhooks(self) -> "WebhookOperations":
        return WebhookOperations(self)

    @property
    def stats(self) -> "StatsOperations":
        return StatsOperations(self)


class ConsentOperations:
    def __init__(self, client: ConsentChainClient):
        self._client = client

    async def list(
        self,
        fiduciary_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[ConsentRecord]:
        params = {"page": page, "page_size": page_size}
        if fiduciary_id:
            params["fiduciary_id"] = str(fiduciary_id)
        if status:
            params["status"] = status

        data = await self._client._request("GET", "/api/v1/consents", params=params)
        return TypeAdapter(List[ConsentRecord]).validate_python(data.get("items", data))

    async def get(self, consent_id: UUID) -> ConsentRecord:
        data = await self._client._request("GET", f"/api/v1/consents/{consent_id}")
        return ConsentRecord.model_validate(data)

    async def create(self, consent: ConsentCreate) -> ConsentRecord:
        data = await self._client._request(
            "POST",
            "/api/v1/consents",
            json=consent.model_dump(mode="json"),
        )
        return ConsentRecord.model_validate(data)

    async def update(self, consent_id: UUID, update: ConsentUpdate) -> ConsentRecord:
        data = await self._client._request(
            "PUT",
            f"/api/v1/consents/{consent_id}",
            json=update.model_dump(mode="json", exclude_unset=True),
        )
        return ConsentRecord.model_validate(data)

    async def grant(self, consent_id: UUID, signature: str) -> ConsentRecord:
        data = await self._client._request(
            "POST",
            f"/api/v1/consents/{consent_id}/grant",
            json={"signature": signature},
        )
        return ConsentRecord.model_validate(data)

    async def revoke(self, consent_id: UUID, reason: Optional[str] = None) -> ConsentRecord:
        payload = {}
        if reason:
            payload["reason"] = reason
        data = await self._client._request(
            "POST",
            f"/api/v1/consents/{consent_id}/revoke",
            json=payload,
        )
        return ConsentRecord.model_validate(data)

    async def verify(self, consent_hash: str) -> Dict[str, Any]:
        return await self._client._request(
            "GET",
            f"/api/v1/consents/verify/{consent_hash}",
        )


class FiduciaryOperations:
    def __init__(self, client: ConsentChainClient):
        self._client = client

    async def list(self) -> List[Fiduciary]:
        data = await self._client._request("GET", "/api/v1/fiduciaries")
        return TypeAdapter(List[Fiduciary]).validate_python(data)

    async def get(self, fiduciary_id: UUID) -> Fiduciary:
        data = await self._client._request("GET", f"/api/v1/fiduciaries/{fiduciary_id}")
        return Fiduciary.model_validate(data)

    async def create(
        self,
        name: str,
        registration_number: str,
        wallet_address: str,
        contact_email: str,
        data_categories: List[str],
        purposes: List[str],
    ) -> Fiduciary:
        data = await self._client._request(
            "POST",
            "/api/v1/fiduciaries",
            json={
                "name": name,
                "registration_number": registration_number,
                "wallet_address": wallet_address,
                "contact_email": contact_email,
                "data_categories": data_categories,
                "purposes": purposes,
            },
        )
        return Fiduciary.model_validate(data)

    async def regenerate_api_key(self, fiduciary_id: UUID) -> Dict[str, str]:
        return await self._client._request(
            "POST",
            f"/api/v1/fiduciaries/{fiduciary_id}/regenerate-key",
        )


class PrincipalOperations:
    def __init__(self, client: ConsentChainClient):
        self._client = client

    async def get(self, principal_id: UUID) -> DataPrincipal:
        data = await self._client._request("GET", f"/api/v1/principals/{principal_id}")
        return DataPrincipal.model_validate(data)

    async def get_by_wallet(self, wallet_address: str) -> DataPrincipal:
        data = await self._client._request(
            "GET",
            "/api/v1/principals/by-wallet",
            params={"wallet_address": wallet_address},
        )
        return DataPrincipal.model_validate(data)


class WebhookOperations:
    def __init__(self, client: ConsentChainClient):
        self._client = client

    async def list(self, fiduciary_id: UUID) -> List[WebhookSubscription]:
        data = await self._client._request(
            "GET",
            f"/api/v1/fiduciaries/{fiduciary_id}/webhooks",
        )
        return TypeAdapter(List[WebhookSubscription]).validate_python(data)

    async def create(
        self,
        fiduciary_id: UUID,
        callback_url: str,
        events: List[str],
        secret: str,
    ) -> WebhookSubscription:
        data = await self._client._request(
            "POST",
            f"/api/v1/fiduciaries/{fiduciary_id}/webhooks",
            json={
                "callback_url": callback_url,
                "events": events,
                "secret": secret,
            },
        )
        return WebhookSubscription.model_validate(data)

    async def deliveries(self, subscription_id: UUID) -> List[WebhookDelivery]:
        data = await self._client._request(
            "GET",
            f"/api/v1/webhooks/{subscription_id}/deliveries",
        )
        return TypeAdapter(List[WebhookDelivery]).validate_python(data)


class StatsOperations:
    def __init__(self, client: ConsentChainClient):
        self._client = client

    async def dashboard(self) -> DashboardStats:
        data = await self._client._request("GET", "/api/v1/consents/stats")
        return DashboardStats.model_validate(data)
