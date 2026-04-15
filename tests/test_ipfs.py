"""Tests for IPFS Integration and Consent Evidence Store.

Covers:
- IPFSClient JSON upload and retrieval
- IPFSClient binary upload
- CID pinning and unpinning
- Consent evidence storage
- Revocation evidence storage
- Evidence retrieval
- Content hash computation
- Connection management
"""

import pytest
import json
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from api.ipfs import (
    IPFSClient,
    IPFSConfig,
    IPFSUploadResult,
    ConsentEvidenceStore,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def ipfs_config():
    """Provide test IPFS configuration."""
    return IPFSConfig(
        api_url="https://ipfs.infura.io:5001",
        gateway_url="https://ipfs.io/ipfs",
        project_id="test-project-id",
        project_secret="test-project-secret",
        timeout=30,
    )


@pytest.fixture
def ipfs_client(ipfs_config):
    """Provide an IPFSClient with test config."""
    return IPFSClient(config=ipfs_config)


@pytest.fixture
def sample_consent_data():
    """Provide sample consent data for storage."""
    return {
        "version": "1.0",
        "consent_id": "consent-123",
        "principal_wallet": "P" * 58,
        "fiduciary_wallet": "F" * 58,
        "purpose": "MARKETING",
        "data_types": ["contact_info", "personal_info"],
        "granted_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2027-01-01T00:00:00+00:00",
        "signature": "test-signature",
        "tx_id": "tx-abc123",
        "metadata": {"source": "web"},
    }


# ============================================================
# Test: IPFS Configuration
# ============================================================


class TestIPFSConfig:
    """Test IPFS configuration."""

    def test_default_config(self):
        """Default config uses Infura endpoints."""
        config = IPFSConfig()
        assert "infura.io" in config.api_url
        assert "ipfs.io" in config.gateway_url
        assert config.timeout == 30

    def test_custom_config(self, ipfs_config):
        """Custom config is applied correctly."""
        assert ipfs_config.project_id == "test-project-id"
        assert ipfs_config.project_secret == "test-project-secret"


# ============================================================
# Test: IPFSClient JSON Upload
# ============================================================


class TestIPFSUpload:
    """Test IPFS data upload."""

    @pytest.mark.asyncio
    async def test_upload_json_success(self, ipfs_client, sample_consent_data):
        """JSON data uploads and returns result with CID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Hash": "QmTest123",
            "Name": "consent.json",
            "Size": "256",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            with patch.object(ipfs_client, "pin_cid", return_value=True):
                result = await ipfs_client.upload_json(sample_consent_data)

        assert result.cid == "QmTest123"
        assert result.size == "256"
        assert "QmTest123" in result.url
        assert isinstance(result.uploaded_at, datetime)

    @pytest.mark.asyncio
    async def test_upload_json_error_response(self, ipfs_client, sample_consent_data):
        """Upload error raises httpx exception."""
        from httpx import HTTPStatusError, Request, Response

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "Server error", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            with pytest.raises(HTTPStatusError):
                await ipfs_client.upload_json(sample_consent_data)


# ============================================================
# Test: IPFSClient Binary Upload
# ============================================================


class TestIPFSBinaryUpload:
    """Test binary data upload to IPFS."""

    @pytest.mark.asyncio
    async def test_upload_bytes_success(self, ipfs_client):
        """Binary data uploads successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Hash": "QmBinary456",
            "Name": "data",
            "Size": "1024",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            with patch.object(ipfs_client, "pin_cid", return_value=True):
                result = await ipfs_client.upload_bytes(b"binary-data-here", filename="evidence.bin")

        assert result.cid == "QmBinary456"
        assert result.size == "1024"


# ============================================================
# Test: IPFSClient Data Retrieval
# ============================================================


class TestIPFSRetrieval:
    """Test data retrieval from IPFS."""

    @pytest.mark.asyncio
    async def test_get_json_success(self, ipfs_client):
        """JSON data retrieved by CID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"consent_id": "consent-123", "purpose": "MARKETING"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.ipfs.httpx.AsyncClient", return_value=mock_client):
            result = await ipfs_client.get_json("QmTest123")

        assert result["consent_id"] == "consent-123"
        assert result["purpose"] == "MARKETING"

    @pytest.mark.asyncio
    async def test_get_json_not_found(self, ipfs_client):
        """Missing CID raises error."""
        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "Not found", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.ipfs.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPStatusError):
                await ipfs_client.get_json("QmNonexistent")


# ============================================================
# Test: CID Pinning
# ============================================================


class TestCIDPinning:
    """Test CID pin and unpin operations."""

    @pytest.mark.asyncio
    async def test_pin_cid_success(self, ipfs_client):
        """Successful pin returns True."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            MagicMock(status_code=200),  # pin/add
            MagicMock(
                status_code=200,
                json=MagicMock(return_value={"Keys": {"QmTest123": {"Type": 0}}}),
            ),  # pin/ls
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            result = await ipfs_client.pin_cid("QmTest123")

        assert result is True

    @pytest.mark.asyncio
    async def test_pin_cid_http_error(self, ipfs_client):
        """Pin HTTP error returns False."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            MagicMock(status_code=500),  # pin/add fails
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            result = await ipfs_client.pin_cid("QmTest123")

        assert result is False

    @pytest.mark.asyncio
    async def test_unpin_cid_success(self, ipfs_client):
        """Successful unpin returns True."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            result = await ipfs_client.unpin_cid("QmTest123")

        assert result is True

    @pytest.mark.asyncio
    async def test_unpin_cid_error(self, ipfs_client):
        """Unpin error returns False."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(ipfs_client, "_get_client", return_value=mock_client):
            result = await ipfs_client.unpin_cid("QmTest123")

        assert result is False


# ============================================================
# Test: Consent Evidence Store
# ============================================================


class TestConsentEvidenceStore:
    """Test consent evidence storage on IPFS."""

    @pytest.mark.asyncio
    async def test_store_consent_evidence(self):
        """Consent evidence is stored with correct structure."""
        mock_ipfs = AsyncMock()
        mock_ipfs.upload_json = AsyncMock(return_value=IPFSUploadResult(
            cid="QmConsentEvidence",
            size=512,
            url="https://ipfs.io/ipfs/QmConsentEvidence",
            uploaded_at=datetime.now(timezone.utc),
        ))

        store = ConsentEvidenceStore(ipfs_client=mock_ipfs)
        granted_at = datetime.now(timezone.utc)
        expires_at = granted_at.replace(year=granted_at.year + 1)

        result = await store.store_consent_evidence(
            consent_id="consent-123",
            principal_wallet="P" * 58,
            fiduciary_wallet="F" * 58,
            purpose="MARKETING",
            data_types=["contact_info"],
            granted_at=granted_at,
            expires_at=expires_at,
            signature="sig-abc",
            tx_id="tx-123",
            metadata={"source": "web"},
        )

        assert result.cid == "QmConsentEvidence"
        mock_ipfs.upload_json.assert_called_once()

        # Verify the uploaded data structure
        uploaded_data = mock_ipfs.upload_json.call_args[0][0]
        assert uploaded_data["version"] == "1.0"
        assert uploaded_data["consent_id"] == "consent-123"
        assert uploaded_data["purpose"] == "MARKETING"
        assert uploaded_data["data_types"] == ["contact_info"]
        assert uploaded_data["tx_id"] == "tx-123"
        assert "content_hash" in uploaded_data

    @pytest.mark.asyncio
    async def test_store_consent_evidence_without_optional_fields(self):
        """Consent evidence stored without optional fields."""
        mock_ipfs = AsyncMock()
        mock_ipfs.upload_json = AsyncMock(return_value=IPFSUploadResult(
            cid="QmMinimal",
            size=256,
            url="https://ipfs.io/ipfs/QmMinimal",
            uploaded_at=datetime.now(timezone.utc),
        ))

        store = ConsentEvidenceStore(ipfs_client=mock_ipfs)

        result = await store.store_consent_evidence(
            consent_id="consent-456",
            principal_wallet="P" * 58,
            fiduciary_wallet="F" * 58,
            purpose="SERVICE_DELIVERY",
            data_types=["personal_info"],
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            signature="sig-def",
        )

        uploaded_data = mock_ipfs.upload_json.call_args[0][0]
        assert uploaded_data["expires_at"] is None
        assert uploaded_data["tx_id"] is None
        assert uploaded_data["metadata"] == {}

    @pytest.mark.asyncio
    async def test_store_revocation_evidence(self):
        """Revocation evidence stored correctly."""
        mock_ipfs = AsyncMock()
        mock_ipfs.upload_json = AsyncMock(return_value=IPFSUploadResult(
            cid="QmRevocation",
            size=128,
            url="https://ipfs.io/ipfs/QmRevocation",
            uploaded_at=datetime.now(timezone.utc),
        ))

        store = ConsentEvidenceStore(ipfs_client=mock_ipfs)

        result = await store.store_revocation_evidence(
            consent_id="consent-123",
            revoked_at=datetime.now(timezone.utc),
            revoked_by="principal-wallet",
            reason="No longer needed",
            tx_id="tx-revoke-123",
        )

        assert result.cid == "QmRevocation"

        uploaded_data = mock_ipfs.upload_json.call_args[0][0]
        assert uploaded_data["type"] == "revocation"
        assert uploaded_data["consent_id"] == "consent-123"
        assert uploaded_data["reason"] == "No longer needed"

    @pytest.mark.asyncio
    async def test_store_revocation_without_reason(self):
        """Revocation evidence can omit reason."""
        mock_ipfs = AsyncMock()
        mock_ipfs.upload_json = AsyncMock(return_value=IPFSUploadResult(
            cid="QmRevNoReason",
            size=100,
            url="https://ipfs.io/ipfs/QmRevNoReason",
            uploaded_at=datetime.now(timezone.utc),
        ))

        store = ConsentEvidenceStore(ipfs_client=mock_ipfs)

        result = await store.store_revocation_evidence(
            consent_id="consent-789",
            revoked_at=datetime.now(timezone.utc),
            revoked_by="principal-wallet",
            reason=None,
        )

        uploaded_data = mock_ipfs.upload_json.call_args[0][0]
        assert uploaded_data["reason"] is None

    @pytest.mark.asyncio
    async def test_retrieve_evidence(self):
        """Evidence retrieved by CID."""
        mock_ipfs = AsyncMock()
        expected_data = {
            "version": "1.0",
            "consent_id": "consent-123",
            "purpose": "MARKETING",
        }
        mock_ipfs.get_json = AsyncMock(return_value=expected_data)

        store = ConsentEvidenceStore(ipfs_client=mock_ipfs)
        result = await store.retrieve_evidence("QmConsentEvidence")

        assert result == expected_data
        mock_ipfs.get_json.assert_called_once_with("QmConsentEvidence")


# ============================================================
# Test: Content Hash Computation
# ============================================================


class TestContentHash:
    """Test content hash computation for evidence integrity."""

    def test_compute_hash_is_deterministic(self):
        """Same inputs produce same hash."""
        granted_at = datetime(2026, 1, 1, 12, 0, 0)
        hash1 = ConsentEvidenceStore._compute_hash(
            "consent-123", "P" * 58, "F" * 58, "MARKETING", granted_at
        )
        hash2 = ConsentEvidenceStore._compute_hash(
            "consent-123", "P" * 58, "F" * 58, "MARKETING", granted_at
        )
        assert hash1 == hash2

    def test_compute_hash_different_inputs(self):
        """Different inputs produce different hash."""
        granted_at = datetime(2026, 1, 1, 12, 0, 0)
        hash1 = ConsentEvidenceStore._compute_hash(
            "consent-123", "P" * 58, "F" * 58, "MARKETING", granted_at
        )
        hash2 = ConsentEvidenceStore._compute_hash(
            "consent-456", "P" * 58, "F" * 58, "MARKETING", granted_at
        )
        assert hash1 != hash2

    def test_compute_hash_is_sha256(self):
        """Hash is valid SHA-256 hex string."""
        granted_at = datetime.now(timezone.utc)
        hash_value = ConsentEvidenceStore._compute_hash(
            "consent-123", "P" * 58, "F" * 58, "MARKETING", granted_at
        )
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


# ============================================================
# Test: Client Lifecycle
# ============================================================


class TestClientLifecycle:
    """Test IPFS client connection lifecycle."""

    @pytest.mark.asyncio
    async def test_close_client(self, ipfs_client):
        """Client can be closed."""
        # Set up a mock client
        mock_httpx = AsyncMock()
        mock_httpx.aclose = AsyncMock()
        ipfs_client._client = mock_httpx

        await ipfs_client.close()

        mock_httpx.aclose.assert_awaited_once()
        assert ipfs_client._client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self, ipfs_client):
        """Closing without active client does not error."""
        ipfs_client._client = None
        await ipfs_client.close()  # should not raise

    @pytest.mark.asyncio
    async def test_get_client_with_auth(self, ipfs_config):
        """Client uses basic auth when credentials provided."""
        client = IPFSClient(config=ipfs_config)
        httpx_client = await client._get_client()

        assert httpx_client is not None
        # Headers should include Basic auth
        assert "Authorization" in httpx_client.headers

    def test_default_ipfs_client_has_no_auth(self):
        """Default client has no auth headers."""
        client = IPFSClient()
        assert client.config.project_id is None
        assert client.config.project_secret is None
