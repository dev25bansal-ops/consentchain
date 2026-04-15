"""Tests for Data Portability Service.

Covers:
- Data export in JSON format
- Data export with selective inclusion (consents, audit logs, grievances)
- Data transfer between fiduciaries
- Export format listing
- CSV formatting
- Export verification (hash signing)
- Principal not found handling
"""

import pytest
import json
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from api.portability import (
    DataPortabilityService,
    DataExportRequest,
    DataTransferRequest,
    ExportFormat,
    TransferStatus,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_db_session():
    """Provide a mocked async database session."""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_principal():
    """Provide a mock principal record."""
    principal = MagicMock()
    principal.id = uuid4()
    principal.wallet_address = "P" * 58
    principal.email_hash = hashlib.sha256(b"test@test.com").hexdigest()
    return principal


@pytest.fixture
def sample_consent():
    """Provide a mock consent record."""
    consent = MagicMock()
    consent.id = uuid4()
    consent.fiduciary_id = uuid4()
    consent.principal_id = uuid4()
    consent.purpose = "MARKETING"
    consent.data_types = json.dumps(["contact_info", "personal_info"])
    consent.status = MagicMock()
    consent.status.value = "GRANTED"
    consent.granted_at = datetime.now(timezone.utc)
    consent.expires_at = datetime.now(timezone.utc)
    consent.revoked_at = None
    consent.consent_hash = "abc123hash"
    consent.created_at = datetime.now(timezone.utc)
    return consent


@pytest.fixture
def export_request(sample_principal):
    """Provide a standard export request."""
    return DataExportRequest(
        principal_id=sample_principal.id,
        format=ExportFormat.JSON,
        include_audit_logs=True,
        include_consents=True,
        include_grievances=True,
    )


# ============================================================
# Test: Data Export
# ============================================================


class TestDataExport:
    """Test data export functionality."""

    @pytest.mark.asyncio
    async def test_export_json_success(self, mock_db_session, sample_principal, sample_consent):
        """JSON export returns structured data with verification."""
        mock_db_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_principal)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_consent])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        service = DataPortabilityService(mock_db_session)
        request = DataExportRequest(
            principal_id=sample_principal.id,
            format=ExportFormat.JSON,
            include_consents=True,
            include_audit_logs=True,
            include_grievances=True,
        )
        result = await service.export_principal_data(request)

        assert "export_metadata" in result
        assert "data" in result
        assert "verification" in result
        assert "consents" in result["data"]
        assert len(result["data"]["consents"]) == 1

    @pytest.mark.asyncio
    async def test_export_metadata_fields(self, mock_db_session, sample_principal, sample_consent):
        """Export metadata contains required fields."""
        mock_db_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_principal)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        service = DataPortabilityService(mock_db_session)
        request = DataExportRequest(
            principal_id=sample_principal.id,
            format=ExportFormat.JSON,
            include_consents=True,
            include_audit_logs=False,
            include_grievances=False,
        )
        result = await service.export_principal_data(request)

        meta = result["export_metadata"]
        assert "export_id" in meta
        assert meta["principal_id"] == str(sample_principal.id)
        assert meta["principal_wallet"] == sample_principal.wallet_address
        assert meta["format"] == "json"
        assert meta["version"] == "1.0"
        assert meta["generator"] == "ConsentChain DPDP Compliance System"

    @pytest.mark.asyncio
    async def test_export_verification_hash(self, mock_db_session, sample_principal, sample_consent):
        """Export includes SHA-256 verification hash."""
        mock_db_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_principal)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_consent])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        service = DataPortabilityService(mock_db_session)
        request = DataExportRequest(
            principal_id=sample_principal.id,
            format=ExportFormat.JSON,
            include_consents=True,
            include_audit_logs=False,
            include_grievances=False,
        )
        result = await service.export_principal_data(request)

        verification = result["verification"]
        assert verification["algorithm"] == "SHA-256"
        assert len(verification["hash"]) == 64  # SHA-256 hex length
        assert "signed_at" in verification

    @pytest.mark.asyncio
    async def test_export_principal_not_found(self, mock_db_session):
        """Export for nonexistent principal raises error."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))

        service = DataPortabilityService(mock_db_session)
        request = DataExportRequest(
            principal_id=uuid4(),
            format=ExportFormat.JSON,
        )

        with pytest.raises(ValueError, match="Principal not found"):
            await service.export_principal_data(request)

    @pytest.mark.asyncio
    async def test_export_consent_structure(self, mock_db_session, sample_principal, sample_consent):
        """Exported consent has correct structure."""
        mock_db_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_principal)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_consent])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        service = DataPortabilityService(mock_db_session)
        request = DataExportRequest(
            principal_id=sample_principal.id,
            format=ExportFormat.JSON,
            include_consents=True,
            include_audit_logs=False,
            include_grievances=False,
        )
        result = await service.export_principal_data(request)

        consent_data = result["data"]["consents"][0]
        assert "consent_id" in consent_data
        assert "fiduciary_id" in consent_data
        assert "purpose" in consent_data
        assert "data_types" in consent_data
        assert "status" in consent_data
        assert "consent_hash" in consent_data

    @pytest.mark.asyncio
    async def test_export_date_filtering(self, mock_db_session, sample_principal):
        """Export request supports date range filtering."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        request = DataExportRequest(
            principal_id=sample_principal.id,
            format=ExportFormat.JSON,
            include_consents=True,
            date_from=now - timedelta(days=30),
            date_to=now,
        )

        assert request.date_from is not None
        assert request.date_to is not None


# ============================================================
# Test: Data Transfer
# ============================================================


class TestDataTransfer:
    """Test data transfer between fiduciaries."""

    @pytest.mark.asyncio
    async def test_transfer_creates_record(self, mock_db_session, sample_principal, sample_consent):
        """Transfer creates a structured transfer record."""
        mock_db_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_principal)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_consent])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        service = DataPortabilityService(mock_db_session)
        request = DataTransferRequest(
            principal_id=sample_principal.id,
            source_fiduciary_id=uuid4(),
            target_fiduciary_id=uuid4(),
            data_categories=["NAME", "EMAIL"],
        )

        result = await service.transfer_to_fiduciary(request)

        assert "transfer_id" in result
        assert result["status"] == TransferStatus.PENDING.value
        assert "data_package" in result


# ============================================================
# Test: Export Formats
# ============================================================


class TestExportFormats:
    """Test export format listing."""

    @pytest.mark.asyncio
    async def test_get_export_formats(self, mock_db_session):
        """Returns all supported formats."""
        service = DataPortabilityService(mock_db_session)
        formats = await service.get_export_formats()

        assert len(formats) == 3
        format_names = [f["format"] for f in formats]
        assert "json" in format_names
        assert "csv" in format_names
        assert "xml" in format_names
    @pytest.mark.asyncio
    async def test_format_details(self, mock_db_session):
        """Each format has description and mime type."""
        service = DataPortabilityService(mock_db_session)
        formats = await service.get_export_formats()

        json_format = next(f for f in formats if f["format"] == "json")
        assert "machine-readable" in json_format["description"].lower()
        assert json_format["mime_type"] == "application/json"


# ============================================================
# Test: CSV Formatting
# ============================================================


class TestCSVFormatting:
    """Test CSV export formatting."""

    def test_format_as_csv_with_consents(self, mock_db_session):
        """Consent data is formatted as CSV."""
        export_data = {
            "data": {
                "consents": [
                    {
                        "consent_id": "c1",
                        "fiduciary_id": "f1",
                        "purpose": "MARKETING",
                        "status": "GRANTED",
                        "granted_at": "2026-01-01T00:00:00+00:00",
                        "expires_at": "2027-01-01T00:00:00+00:00",
                        "consent_hash": "hash123",
                    },
                    {
                        "consent_id": "c2",
                        "fiduciary_id": "f2",
                        "purpose": "SERVICE_DELIVERY",
                        "status": "REVOKED",
                        "granted_at": "2026-02-01T00:00:00+00:00",
                        "expires_at": None,
                        "consent_hash": "hash456",
                    },
                ]
            }
        }

        service = DataPortabilityService(mock_db_session)
        csv_output = service.format_as_csv(export_data)

        lines = csv_output.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "consent_id" in lines[0]
        assert "c1" in lines[1]
        assert "c2" in lines[2]

    def test_format_as_csv_empty_consents(self, mock_db_session):
        """Empty consent list produces empty CSV."""
        export_data = {"data": {"consents": []}}

        service = DataPortabilityService(mock_db_session)
        csv_output = service.format_as_csv(export_data)

        assert csv_output == ""

    def test_format_as_csv_no_consents_key(self, mock_db_session):
        """Missing consents key produces empty CSV."""
        export_data = {"data": {}}

        service = DataPortabilityService(mock_db_session)
        csv_output = service.format_as_csv(export_data)

        assert csv_output == ""


# ============================================================
# Test: Pydantic Models
# ============================================================


class TestPortabilityModels:
    """Test portability request models."""

    def test_export_request_defaults(self):
        """Export request has sensible defaults."""
        request = DataExportRequest(principal_id=uuid4())

        assert request.format == ExportFormat.JSON
        assert request.include_audit_logs is True
        assert request.include_consents is True
        assert request.include_grievances is True
        assert request.include_deletion_requests is False

    def test_export_request_custom(self):
        """Export request accepts custom settings."""
        request = DataExportRequest(
            principal_id=uuid4(),
            format=ExportFormat.CSV,
            include_audit_logs=False,
            include_consents=False,
            include_grievances=True,
        )

        assert request.format == ExportFormat.CSV
        assert request.include_audit_logs is False

    def test_transfer_request(self):
        """Transfer request is valid."""
        request = DataTransferRequest(
            principal_id=uuid4(),
            source_fiduciary_id=uuid4(),
            target_fiduciary_id=uuid4(),
            data_categories=["NAME", "EMAIL"],
        )

        assert len(request.data_categories) == 2
