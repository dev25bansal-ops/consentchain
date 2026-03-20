import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4
import json

import sys

sys.path.insert(0, ".")

from sdk.client import (
    ConsentChainClient,
    ConsentRecord,
    ConsentRequest,
    VerificationResult,
    ConsentStatus,
    ConsentPurpose,
    DataType,
    quick_verify,
    create_consent_simple,
)


class MockResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class TestConsentChainClient:
    @pytest.fixture
    def client(self):
        return ConsentChainClient(
            api_url="http://localhost:8000",
            api_key="test_api_key",
            fiduciary_id=str(uuid4()),
        )

    def test_client_initialization(self, client):
        assert client.api_url == "http://localhost:8000"
        assert client.api_key == "test_api_key"
        assert client.timeout == 30
        assert client.retry_count == 3

    @patch("httpx.Client")
    def test_create_consent(self, mock_httpx, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "consent_id": str(uuid4()),
                "status": "GRANTED",
                "granted_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                "on_chain_tx_id": "abc123",
                "consent_hash": "hash123",
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        result = client.create_consent(
            principal_wallet="TEST_WALLET_ADDRESS",
            purpose="MARKETING",
            data_types=["PERSONAL_INFO"],
            duration_days=90,
        )

        assert isinstance(result, ConsentRecord)
        assert result.purpose == "MARKETING"
        assert result.status == "GRANTED"

    @patch("httpx.Client")
    def test_verify_consent_valid(self, mock_httpx, client):
        consent_id = str(uuid4())
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "valid": True,
                "consent_id": consent_id,
                "purpose": "MARKETING",
                "data_types": ["PERSONAL_INFO"],
                "granted_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        result = client.verify_consent(consent_id)

        assert isinstance(result, VerificationResult)
        assert result.valid is True
        assert result.purpose == "MARKETING"

    @patch("httpx.Client")
    def test_verify_consent_invalid(self, mock_httpx, client):
        consent_id = str(uuid4())
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "data": {
                "valid": False,
                "reason": "Consent revoked",
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        result = client.verify_consent(consent_id)

        assert result.valid is False
        assert result.reason == "Consent revoked"

    @patch("httpx.Client")
    def test_query_consents(self, mock_httpx, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "consents": [
                    {
                        "consent_id": str(uuid4()),
                        "principal_id": str(uuid4()),
                        "fiduciary_id": client.fiduciary_id,
                        "purpose": "MARKETING",
                        "data_types": ["PERSONAL_INFO"],
                        "status": "GRANTED",
                        "granted_at": datetime.utcnow().isoformat(),
                        "expires_at": None,
                        "on_chain_tx_id": "tx123",
                        "consent_hash": "hash123",
                    }
                ]
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        results = client.query_consents(status="GRANTED")

        assert len(results) == 1
        assert results[0].status == "GRANTED"

    @patch("httpx.Client")
    def test_batch_create_consents(self, mock_httpx, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "results": [
                    {"principal_wallet": "addr1", "consent_id": str(uuid4()), "success": True},
                    {"principal_wallet": "addr2", "consent_id": str(uuid4()), "success": True},
                ]
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        requests = [
            ConsentRequest(
                principal_wallet="addr1",
                purpose="MARKETING",
                data_types=["PERSONAL_INFO"],
                duration_days=90,
            ),
            ConsentRequest(
                principal_wallet="addr2",
                purpose="ANALYTICS",
                data_types=["BEHAVIORAL_DATA"],
                duration_days=180,
            ),
        ]

        result = client.batch_create_consents(requests)

        assert result["success"] is True

    @patch("httpx.Client")
    def test_generate_compliance_report(self, mock_httpx, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "report_id": str(uuid4()),
                "fiduciary_id": client.fiduciary_id,
                "total_consents": 100,
                "active_consents": 80,
                "revoked_consents": 15,
                "expired_consents": 5,
                "compliance_score": 95,
            },
        }
        mock_response.raise_for_status = Mock()

        client._client = mock_httpx.return_value
        client._client.request.return_value = mock_response

        result = client.generate_compliance_report(
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
        )

        assert "report_id" in result
        assert result["compliance_score"] == 95


class TestConsentRecord:
    def test_consent_record_creation(self):
        record = ConsentRecord(
            consent_id=str(uuid4()),
            principal_id=str(uuid4()),
            fiduciary_id=str(uuid4()),
            purpose="MARKETING",
            data_types=["PERSONAL_INFO", "CONTACT_INFO"],
            status="GRANTED",
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
        )

        assert record.status == "GRANTED"
        assert len(record.data_types) == 2


class TestVerificationResult:
    def test_verification_result_valid(self):
        result = VerificationResult(
            valid=True,
            consent_id=str(uuid4()),
            purpose="MARKETING",
            data_types=["PERSONAL_INFO"],
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
        )

        assert result.valid is True
        assert result.reason is None

    def test_verification_result_invalid(self):
        result = VerificationResult(
            valid=False,
            reason="Consent expired",
        )

        assert result.valid is False
        assert result.reason == "Consent expired"


class TestEnums:
    def test_consent_status_values(self):
        assert ConsentStatus.GRANTED.value == "GRANTED"
        assert ConsentStatus.REVOKED.value == "REVOKED"
        assert ConsentStatus.EXPIRED.value == "EXPIRED"

    def test_consent_purpose_values(self):
        assert ConsentPurpose.MARKETING.value == "MARKETING"
        assert ConsentPurpose.ANALYTICS.value == "ANALYTICS"
        assert ConsentPurpose.THIRD_PARTY_SHARING.value == "THIRD_PARTY_SHARING"

    def test_data_type_values(self):
        assert DataType.PERSONAL_INFO.value == "PERSONAL_INFO"
        assert DataType.SENSITIVE_DATA.value == "SENSITIVE_DATA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
