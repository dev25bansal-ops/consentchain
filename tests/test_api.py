import pytest
from httpx import AsyncClient
from uuid import uuid4
import json

from sqlalchemy.ext.asyncio import AsyncSession
from api.database import (
    DataFiduciaryDB,
    DataPrincipalDB,
    ConsentRecordDB,
    ConsentStatusDB,
)
from tests.conftest import auth_headers


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestFiduciaryRegistration:
    @pytest.mark.asyncio
    async def test_register_fiduciary_success(self, client: AsyncClient):
        payload = {
            "name": "New Test Company",
            "registration_number": f"REG_{uuid4().hex[:8].upper()}",
            "contact_email": "newcompany@test.com",
            "data_categories": ["FINANCIAL", "PERSONAL"],
            "purposes": ["KYC Verification"],
        }
        response = await client.post("/api/v1/fiduciary/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "api_key" in data["data"]
        assert "fiduciary_id" in data["data"]

    @pytest.mark.asyncio
    async def test_register_fiduciary_duplicate_registration(
        self, client: AsyncClient, test_fiduciary: DataFiduciaryDB
    ):
        payload = {
            "name": "Duplicate Company",
            "registration_number": test_fiduciary.registration_number,
            "contact_email": "duplicate@test.com",
            "data_categories": ["FINANCIAL"],
            "purposes": ["Testing"],
        }
        response = await client.post("/api/v1/fiduciary/register", json=payload)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_fiduciary_missing_fields(self, client: AsyncClient):
        payload = {"name": "Incomplete Company"}
        response = await client.post("/api/v1/fiduciary/register", json=payload)
        assert response.status_code == 422


class TestConsentCreation:
    @pytest.mark.asyncio
    async def test_create_consent_success(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
        auth_headers: dict,
    ):
        payload = {
            "principal_wallet": "C" * 58,
            "fiduciary_id": str(test_fiduciary.id),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME", "EMAIL", "PHONE"],
            "duration_days": 90,
            "signature": "test_signature_placeholder",
        }
        response = await client.post(
            "/api/v1/consent/create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "consent_id" in data["data"]
        assert data["data"]["status"] == "GRANTED"

    @pytest.mark.asyncio
    async def test_create_consent_invalid_fiduciary(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "principal_wallet": "C" * 58,
            "fiduciary_id": str(uuid4()),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 30,
            "signature": "test",
        }
        response = await client.post(
            "/api/v1/consent/create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_consent_invalid_wallet_address(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
        auth_headers: dict,
    ):
        payload = {
            "principal_wallet": "invalid_address",
            "fiduciary_id": str(test_fiduciary.id),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 30,
            "signature": "test",
        }
        response = await client.post(
            "/api/v1/consent/create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_consent_invalid_duration(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
        auth_headers: dict,
    ):
        payload = {
            "principal_wallet": "C" * 58,
            "fiduciary_id": str(test_fiduciary.id),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 500,
            "signature": "test",
        }
        response = await client.post(
            "/api/v1/consent/create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_consent_without_auth(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
    ):
        payload = {
            "principal_wallet": "C" * 58,
            "fiduciary_id": str(test_fiduciary.id),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 30,
            "signature": "test",
        }
        response = await client.post("/api/v1/consent/create", json=payload)
        assert response.status_code == 403


class TestConsentQuery:
    @pytest.mark.asyncio
    async def test_query_consents_success(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/consent/query", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "consents" in data["data"]

    @pytest.mark.asyncio
    async def test_query_consents_with_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/consent/query?page=1&limit=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data["data"]
        assert "page" in data["data"]

    @pytest.mark.asyncio
    async def test_query_consents_with_status_filter(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/consent/query?status=GRANTED", headers=auth_headers)
        assert response.status_code == 200


class TestConsentRevocation:
    @pytest.mark.asyncio
    async def test_revoke_consent_success(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        jwt_headers: dict,
    ):
        payload = {
            "consent_id": str(test_consent.id),
            "reason": "User requested revocation",
            "signature": "test_signature",
        }
        response = await client.post(
            "/api/v1/consent/revoke",
            json=payload,
            headers=jwt_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_consent(self, client: AsyncClient, jwt_headers: dict):
        payload = {
            "consent_id": str(uuid4()),
            "reason": "Test",
            "signature": "test",
        }
        response = await client.post(
            "/api/v1/consent/revoke",
            json=payload,
            headers=jwt_headers,
        )
        assert response.status_code == 400


class TestConsentVerification:
    @pytest.mark.asyncio
    async def test_verify_consent_success(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        auth_headers: dict,
    ):
        payload = {
            "consent_id": str(test_consent.id),
        }
        response = await client.post("/api/v1/consent/verify", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data["data"]


class TestPublicEndpoints:
    @pytest.mark.asyncio
    async def test_list_public_fiduciaries(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
    ):
        response = await client.get("/api/v1/public/fiduciaries")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "fiduciaries" in data["data"]
        assert len(data["data"]["fiduciaries"]) > 0

    @pytest.mark.asyncio
    async def test_public_consent_create(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
    ):
        payload = {
            "principal_wallet": "D" * 58,
            "fiduciary_id": str(test_fiduciary.id),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME", "EMAIL"],
            "duration_days": 60,
            "signature": "public_signature",
        }
        response = await client.post(
            "/api/v1/public/consent/create",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "consent_id" in data["data"]


class TestConsentHistory:
    @pytest.mark.asyncio
    async def test_get_consent_history(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        jwt_headers: dict,
    ):
        response = await client.get(
            f"/api/v1/consent/{test_consent.id}/history", headers=jwt_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data["data"]


class TestAuditEndpoints:
    @pytest.mark.asyncio
    async def test_audit_query(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        auth_headers: dict,
    ):
        payload = {
            "page": 1,
            "limit": 20,
        }
        response = await client.post(
            "/api/v1/audit/query",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_granted" in data["data"]
        assert "total_revoked" in data["data"]


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_404_for_unknown_route(self, client: AsyncClient):
        response = await client.get("/api/v1/unknown/endpoint")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        response = await client.delete("/health")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_invalid_json(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/consent/create",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


class TestGrievanceEndpoints:
    @pytest.mark.asyncio
    async def test_submit_grievance(
        self,
        client: AsyncClient,
        test_fiduciary: DataFiduciaryDB,
        test_principal: DataPrincipalDB,
    ):
        payload = {
            "principal_id": str(test_principal.id),
            "fiduciary_id": str(test_fiduciary.id),
            "grievance_type": "ACCESS",
            "subject": "Cannot access my data",
            "description": "I am unable to access my personal data despite multiple requests.",
        }
        response = await client.post("/api/v1/grievance/submit", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "grievance_id" in data["data"]

    @pytest.mark.asyncio
    async def test_list_grievances(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/grievance/list", headers=auth_headers)
        assert response.status_code == 200


class TestGuardianEndpoints:
    @pytest.mark.asyncio
    async def test_register_guardian(self, client: AsyncClient, test_principal: DataPrincipalDB):
        payload = {
            "guardian_wallet": "G" * 58,
            "guardian_name": "Test Guardian",
            "guardian_email": "guardian@test.com",
            "guardian_phone": "+1234567890",
            "guardian_type": "PARENT",
            "principal_id": str(test_principal.id),
            "principal_category": "MINOR",
            "scope": ["CONSENT_MANAGE", "DATA_ACCESS"],
            "valid_from": "2026-01-01T00:00:00",
        }
        response = await client.post("/api/v1/guardian/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeletionEndpoints:
    @pytest.mark.asyncio
    async def test_request_deletion(
        self,
        client: AsyncClient,
        test_principal: DataPrincipalDB,
        test_fiduciary: DataFiduciaryDB,
        jwt_headers: dict,
    ):
        payload = {
            "principal_id": str(test_principal.id),
            "fiduciary_id": str(test_fiduciary.id),
            "scope": "FULL",
            "reason": "Testing deletion request",
        }
        response = await client.post("/api/v1/deletion/request", json=payload, headers=jwt_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data["data"]


class TestAuthenticationEndpoints:
    @pytest.mark.asyncio
    async def test_auth_login_missing_signature(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "wallet_address": "A" * 58,
                "signature": "",
                "message": "test",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_refresh_missing_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""},
        )
        assert response.status_code == 401


class TestTemplateEndpoints:
    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient):
        response = await client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_template_by_category(self, client: AsyncClient):
        response = await client.get("/api/v1/templates?category=CONSENT_REQUEST")
        assert response.status_code == 200


class TestWebhookEndpoints:
    @pytest.mark.skip(reason="Webhook subscription endpoint not yet implemented")
    @pytest.mark.asyncio
    async def test_subscribe_webhook(
        self, client: AsyncClient, test_fiduciary: DataFiduciaryDB, auth_headers: dict
    ):
        payload = {
            "callback_url": "https://example.com/webhook",
            "events": ["CONSENT_GRANTED", "CONSENT_REVOKED"],
            "fiduciary_id": str(test_fiduciary.id),
            "secret": "test_webhook_secret_key_16chars",
        }
        response = await client.post(
            "/api/v1/webhooks/subscribe", json=payload, headers=auth_headers
        )
        assert response.status_code == 200


class TestMetricsAndHealth:
    @pytest.mark.asyncio
    async def test_prometheus_metrics(self, client: AsyncClient):
        response = await client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        assert "consentchain_consents_total" in content
        assert "consentchain_info" in content

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_health_with_dependencies(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        for _ in range(5):
            response = await client.get("/health")
        assert response.status_code == 200


class TestInputValidation:
    @pytest.mark.asyncio
    async def test_invalid_wallet_address(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "principal_wallet": "invalid_wallet",
            "fiduciary_id": str(uuid4()),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 30,
            "signature": "test",
        }
        response = await client.post("/api/v1/consent/create", json=payload, headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_duration(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "principal_wallet": "A" * 58,
            "fiduciary_id": str(uuid4()),
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["NAME"],
            "duration_days": 500,
            "signature": "test",
        }
        response = await client.post("/api/v1/consent/create", json=payload, headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient):
        payload = {"name": "Test"}
        response = await client.post("/api/v1/fiduciary/register", json=payload)
        assert response.status_code == 422


class TestBreachEndpoints:
    @pytest.mark.asyncio
    async def test_create_breach(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        payload = {
            "breach_type": "UNAUTHORIZED_ACCESS",
            "severity": "HIGH",
            "description": "Unauthorized access to personal data detected in system logs affecting multiple user accounts.",
            "affected_principals_count": 100,
            "data_categories_involved": ["NAME", "EMAIL", "PHONE"],
            "containment_measures": ["System locked down", "Passwords reset"],
        }
        response = await client.post("/api/v1/breach/create", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "breach_id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_breach_invalid_type(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "breach_type": "INVALID_TYPE",
            "severity": "HIGH",
            "description": "Test breach description that is long enough.",
            "affected_principals_count": 10,
            "data_categories_involved": ["NAME"],
        }
        response = await client.post("/api/v1/breach/create", json=payload, headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_check_breach_deadlines(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/breach/check-deadlines", headers=auth_headers)
        assert response.status_code == 200


class TestPortabilityEndpoints:
    @pytest.mark.asyncio
    async def test_get_export_formats(self, client: AsyncClient):
        response = await client.get("/api/v1/portability/formats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "formats" in data["data"]

    @pytest.mark.asyncio
    async def test_export_data_json(self, client: AsyncClient, jwt_headers: dict):
        payload = {
            "format": "json",
            "include_audit_logs": True,
            "include_consents": True,
        }
        response = await client.post(
            "/api/v1/portability/export", json=payload, headers=jwt_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_export_data_invalid_format(self, client: AsyncClient, jwt_headers: dict):
        payload = {
            "format": "invalid_format",
            "include_consents": True,
        }
        response = await client.post(
            "/api/v1/portability/export", json=payload, headers=jwt_headers
        )
        assert response.status_code == 400


class TestConsentRenewal:
    @pytest.mark.asyncio
    async def test_get_expiring_consents(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        jwt_headers: dict,
    ):
        response = await client.get("/api/v1/consent/expiring?days=60", headers=jwt_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_renew_consent(
        self,
        client: AsyncClient,
        test_consent: ConsentRecordDB,
        jwt_headers: dict,
    ):
        payload = {
            "duration_days": 365,
            "signature": "test_signature",
        }
        response = await client.post(
            f"/api/v1/consent/{test_consent.id}/renew",
            json=payload,
            headers=jwt_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "new_consent_id" in data["data"]

    @pytest.mark.asyncio
    async def test_renew_consent_invalid_duration(
        self, client: AsyncClient, test_consent: ConsentRecordDB, jwt_headers: dict
    ):
        payload = {
            "duration_days": 10000,
        }
        response = await client.post(
            f"/api/v1/consent/{test_consent.id}/renew",
            json=payload,
            headers=jwt_headers,
        )
        assert response.status_code == 422


class TestDetailedHealth:
    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient):
        response = await client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
