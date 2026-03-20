from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import json
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum


class ConsentStatus(str, Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    MODIFIED = "MODIFIED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class ConsentPurpose(str, Enum):
    MARKETING = "MARKETING"
    ANALYTICS = "ANALYTICS"
    SERVICE_DELIVERY = "SERVICE_DELIVERY"
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    RESEARCH = "RESEARCH"
    COMPLIANCE = "COMPLIANCE"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"


class DataType(str, Enum):
    PERSONAL_INFO = "PERSONAL_INFO"
    CONTACT_INFO = "CONTACT_INFO"
    FINANCIAL_DATA = "FINANCIAL_DATA"
    HEALTH_DATA = "HEALTH_DATA"
    LOCATION_DATA = "LOCATION_DATA"
    BEHAVIORAL_DATA = "BEHAVIORAL_DATA"
    BIOMETRIC_DATA = "BIOMETRIC_DATA"
    SENSITIVE_DATA = "SENSITIVE_DATA"


@dataclass
class ConsentRecord:
    consent_id: str
    principal_id: str
    fiduciary_id: str
    purpose: str
    data_types: List[str]
    status: str
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    on_chain_tx_id: Optional[str] = None
    consent_hash: Optional[str] = None


@dataclass
class ConsentRequest:
    principal_wallet: str
    purpose: str
    data_types: List[str]
    duration_days: int = 365
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    valid: bool
    consent_id: Optional[str] = None
    purpose: Optional[str] = None
    data_types: Optional[List[str]] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


class ConsentChainClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        fiduciary_id: str,
        timeout: int = 30,
        retry_count: int = 3,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.fiduciary_id = fiduciary_id
        self.timeout = timeout
        self.retry_count = retry_count

        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Fiduciary-ID": fiduciary_id,
            },
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        last_exception = None

        for attempt in range(self.retry_count):
            try:
                response = self._client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    raise PermissionError(f"Authentication failed: {e.response.text}")
                if e.response.status_code == 400:
                    raise ValueError(f"Bad request: {e.response.text}")
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < self.retry_count - 1:
                time.sleep(2**attempt)

        raise ConnectionError(f"Failed after {self.retry_count} retries: {last_exception}")

    def create_consent(
        self,
        principal_wallet: str,
        purpose: str,
        data_types: List[str],
        duration_days: int = 365,
        metadata: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
    ) -> ConsentRecord:
        payload = {
            "principal_wallet": principal_wallet,
            "fiduciary_id": self.fiduciary_id,
            "purpose": purpose,
            "data_types": data_types,
            "duration_days": duration_days,
            "metadata": metadata or {},
            "signature": signature or self._generate_signature(principal_wallet),
        }

        response = self._request("POST", "/api/v1/consent/create", json=payload)

        if not response.get("success"):
            raise ValueError(response.get("message", "Failed to create consent"))

        data = response["data"]
        return ConsentRecord(
            consent_id=data["consent_id"],
            principal_id=data.get("principal_id", principal_wallet),
            fiduciary_id=self.fiduciary_id,
            purpose=purpose,
            data_types=data_types,
            status=data["status"],
            granted_at=datetime.fromisoformat(data["granted_at"])
            if data.get("granted_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            on_chain_tx_id=data.get("on_chain_tx_id"),
            consent_hash=data.get("consent_hash"),
        )

    def batch_create_consents(
        self,
        consent_requests: List[ConsentRequest],
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        consents_payload = [
            {
                "principal_wallet": req.principal_wallet,
                "fiduciary_id": self.fiduciary_id,
                "purpose": req.purpose,
                "data_types": req.data_types,
                "duration_days": req.duration_days,
                "metadata": req.metadata,
                "signature": self._generate_signature(req.principal_wallet),
            }
            for req in consent_requests
        ]

        payload = {
            "consents": consents_payload,
            "batch_id": batch_id,
        }

        response = self._request("POST", "/api/v1/consent/batch", json=payload)
        return response

    def verify_consent(
        self,
        consent_id: str,
        principal_id: Optional[str] = None,
    ) -> VerificationResult:
        payload = {
            "consent_id": consent_id,
            "principal_id": principal_id,
        }

        response = self._request("POST", "/api/v1/consent/verify", json=payload)
        data = response.get("data", {})

        return VerificationResult(
            valid=data.get("valid", False),
            consent_id=data.get("consent_id"),
            purpose=data.get("purpose"),
            data_types=data.get("data_types"),
            granted_at=datetime.fromisoformat(data["granted_at"])
            if data.get("granted_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            reason=data.get("reason"),
        )

    def query_consents(
        self,
        principal_id: Optional[str] = None,
        status: Optional[str] = None,
        purpose: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[ConsentRecord]:
        params = {
            "fiduciary_id": self.fiduciary_id,
            "page": page,
            "limit": limit,
        }

        if principal_id:
            params["principal_id"] = principal_id
        if status:
            params["status"] = status
        if purpose:
            params["purpose"] = purpose
        if from_date:
            params["from_date"] = from_date.isoformat()
        if to_date:
            params["to_date"] = to_date.isoformat()

        response = self._request("GET", "/api/v1/consent/query", params=params)

        consents = []
        for item in response.get("data", {}).get("consents", []):
            consents.append(
                ConsentRecord(
                    consent_id=item["consent_id"],
                    principal_id=item["principal_id"],
                    fiduciary_id=item["fiduciary_id"],
                    purpose=item["purpose"],
                    data_types=item["data_types"],
                    status=item["status"],
                    granted_at=datetime.fromisoformat(item["granted_at"])
                    if item.get("granted_at")
                    else None,
                    expires_at=datetime.fromisoformat(item["expires_at"])
                    if item.get("expires_at")
                    else None,
                    revoked_at=datetime.fromisoformat(item["revoked_at"])
                    if item.get("revoked_at")
                    else None,
                    on_chain_tx_id=item.get("on_chain_tx_id"),
                    consent_hash=item.get("consent_hash"),
                )
            )

        return consents

    def get_consent_history(self, consent_id: str) -> List[Dict[str, Any]]:
        response = self._request("GET", f"/api/v1/consent/{consent_id}/history")
        return response.get("data", {}).get("events", [])

    def get_audit_logs(
        self,
        principal_id: Optional[str] = None,
        event_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        payload = {
            "fiduciary_id": self.fiduciary_id,
            "page": page,
            "limit": limit,
        }

        if principal_id:
            payload["principal_id"] = principal_id
        if event_type:
            payload["event_type"] = event_type
        if from_date:
            payload["from_date"] = from_date.isoformat()
        if to_date:
            payload["to_date"] = to_date.isoformat()

        response = self._request("POST", "/api/v1/audit/query", json=payload)
        return response.get("data", {}).get("logs", [])

    def generate_compliance_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        payload = {
            "fiduciary_id": self.fiduciary_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

        response = self._request("POST", "/api/v1/compliance/report", json=payload)
        return response.get("data", {})

    def get_compliance_status(self) -> Dict[str, Any]:
        response = self._request("GET", f"/api/v1/compliance/status/{self.fiduciary_id}")
        return response.get("data", {})

    def check_consent_before_action(
        self,
        principal_id: str,
        purpose: str,
        data_types: List[str],
    ) -> VerificationResult:
        consents = self.query_consents(
            principal_id=principal_id,
            status="GRANTED",
            purpose=purpose,
        )

        for consent in consents:
            if consent.status == "GRANTED":
                if set(data_types).issubset(set(consent.data_types)):
                    if consent.expires_at and consent.expires_at > datetime.utcnow():
                        return self.verify_consent(consent.consent_id, principal_id)

        return VerificationResult(
            valid=False,
            reason="No valid consent found for the specified purpose and data types",
        )

    def _generate_signature(self, data: str) -> str:
        signature_data = f"{data}:{self.fiduciary_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(signature_data.encode()).hexdigest()


class ConsentMiddleware:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        fiduciary_id: str,
        required_purposes: Optional[List[str]] = None,
    ):
        self.client = ConsentChainClient(api_url, api_key, fiduciary_id)
        self.required_purposes = required_purposes or []

    def __call__(self, principal_id: str, purpose: str, data_types: List[str]):
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = self.client.check_consent_before_action(principal_id, purpose, data_types)

                if not result.valid:
                    raise PermissionError(f"Consent verification failed: {result.reason}")

                return func(*args, **kwargs)

            return wrapper

        return decorator

    def verify_and_execute(
        self,
        principal_id: str,
        purpose: str,
        data_types: List[str],
        action,
        *args,
        **kwargs,
    ):
        result = self.client.check_consent_before_action(principal_id, purpose, data_types)

        if not result.valid:
            raise PermissionError(f"Consent verification failed: {result.reason}")

        return action(*args, **kwargs)


def quick_verify(api_url: str, api_key: str, consent_id: str) -> VerificationResult:
    with ConsentChainClient(api_url, api_key, "quick_verify") as client:
        return client.verify_consent(consent_id)


def create_consent_simple(
    api_url: str,
    api_key: str,
    fiduciary_id: str,
    principal_wallet: str,
    purpose: str,
    data_types: List[str],
    duration_days: int = 365,
) -> ConsentRecord:
    with ConsentChainClient(api_url, api_key, fiduciary_id) as client:
        return client.create_consent(
            principal_wallet=principal_wallet,
            purpose=purpose,
            data_types=data_types,
            duration_days=duration_days,
        )
