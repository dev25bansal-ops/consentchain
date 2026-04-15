"""Tests for Breach Notification System.

Covers:
- Breach creation and status tracking
- Authority notification (DPBI) within 72 hours
- Principal notification
- Deadline checking and alerts
- Status transitions
- Breach listing and filtering
- Email template generation
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from api.breach import (
    BreachNotificationService,
    BreachNotificationTemplate,
    BreachCreate,
    BreachUpdate,
    BreachSeverity,
    BreachStatus,
    BreachType,
    BreachRecord,
    AuthorityNotification,
    PrincipalNotification,
)


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def breach_create_data():
    return BreachCreate(
        fiduciary_id=uuid4(),
        breach_type=BreachType.UNAUTHORIZED_ACCESS,
        severity=BreachSeverity.HIGH,
        description="Unauthorized access to personal data detected in system logs affecting multiple user accounts with sensitive information exposure.",
        detected_at=datetime.now(timezone.utc) - timedelta(hours=2),
        affected_principals_count=150,
        data_categories_involved=["NAME", "EMAIL", "PHONE", "FINANCIAL"],
        containment_measures=["System locked down", "Passwords reset"],
    )


class FakeRecord:
    def __init__(self, **kw):
        self.id = kw.get("id", uuid4())
        self.fiduciary_id = kw.get("fiduciary_id", uuid4())
        self.breach_type = kw.get("breach_type", "DATA_EXFILTRATION")
        self.severity = kw.get("severity", "CRITICAL")
        self.status = kw.get("status", "DETECTED")
        self.detected_at = kw.get("detected_at", datetime.now(timezone.utc) - timedelta(hours=24))
        self.description = kw.get("description", "Test breach.")
        self.affected_principals_count = kw.get("affected_principals_count", 500)
        self.data_categories_involved = kw.get("data_categories_involved", '["NAME", "EMAIL"]')
        self.containment_measures = kw.get("containment_measures", '["Isolated"]')
        self.third_parties_involved = kw.get("third_parties_involved", None)
        self.authority_notified_at = kw.get("authority_notified_at", None)
        self.principals_notified_at = kw.get("principals_notified_at", None)
        self.resolved_at = kw.get("resolved_at", None)
        self.created_at = kw.get("created_at", datetime.now(timezone.utc) - timedelta(hours=24))


def ok(scalar=None, scalars=None):
    r = MagicMock()
    if scalar is not None:
        r.scalar_one_or_none.return_value = scalar
        r.scalar_one.return_value = scalar
    if scalars is not None:
        r.scalars.return_value.all.return_value = scalars
    return r


class TestBreachCreation:
    @pytest.mark.asyncio
    async def test_create_breach_success(self, mock_db_session, breach_create_data):
        service = BreachNotificationService(mock_db_session)
        record = await service.create_breach(breach_create_data)
        assert record.status == BreachStatus.DETECTED
        assert record.breach_type == BreachType.UNAUTHORIZED_ACCESS
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_breach_without_containment(self, mock_db_session):
        data = BreachCreate(
            fiduciary_id=uuid4(), breach_type=BreachType.MALWARE,
            severity=BreachSeverity.MEDIUM,
            description="Malware detected on workstation requiring investigation.",
            detected_at=datetime.now(timezone.utc),
            affected_principals_count=10,
            data_categories_involved=["PERSONAL"],
        )
        service = BreachNotificationService(mock_db_session)
        record = await service.create_breach(data)
        assert record.containment_measures is None


class TestAuthorityNotification:
    @pytest.mark.asyncio
    async def test_notify_authority_success(self, mock_db_session):
        rec = FakeRecord()
        mock_db_session.execute.return_value = ok(scalar=rec)
        service = BreachNotificationService(mock_db_session)
        n = await service.notify_authority(breach_id=rec.id, notified_by="dpo@test.com")
        assert n.authority_name == "Data Protection Board of India"
        assert n.reference_number.startswith("DPBI-")

    @pytest.mark.asyncio
    async def test_notify_authority_not_found(self, mock_db_session):
        mock_db_session.execute.return_value = ok(scalar=None)
        service = BreachNotificationService(mock_db_session)
        with pytest.raises(ValueError):
            await service.notify_authority(breach_id=uuid4(), notified_by="dpo@test.com")


class TestPrincipalNotification:
    @pytest.mark.asyncio
    async def test_notify_principals_returns_list(self, mock_db_session):
        rec = FakeRecord()
        calls = [0]
        def se(*a, **kw):
            calls[0] += 1
            return ok(scalar=rec if calls[0] == 1 else None)
        mock_db_session.execute.side_effect = se
        service = BreachNotificationService(mock_db_session)
        with patch("api.notifications.NotificationService") as M:
            m = MagicMock()
            M.return_value = m
            m.send_email = AsyncMock(return_value=MagicMock(success=False))
            m.create_notification = AsyncMock(return_value=True)
            result = await service.notify_principals(breach_id=rec.id, principal_ids=[uuid4()])
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_notify_principals_not_found(self, mock_db_session):
        mock_db_session.execute.return_value = ok(scalar=None)
        service = BreachNotificationService(mock_db_session)
        with pytest.raises(ValueError):
            await service.notify_principals(breach_id=uuid4(), principal_ids=[uuid4()])


class TestBreachStatusUpdates:
    @pytest.mark.asyncio
    async def test_update_status_commits(self, mock_db_session):
        """Status update executes DB update and commits."""
        rec = FakeRecord()
        mock_db_session.execute.return_value = ok(scalar=rec)
        service = BreachNotificationService(mock_db_session)
        await service.update_breach_status(breach_id=rec.id, status=BreachStatus.CONTAINED)
        mock_db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_to_resolved(self, mock_db_session):
        """Resolving a breach executes DB update."""
        rec = FakeRecord()
        mock_db_session.execute.return_value = ok(scalar=rec)
        service = BreachNotificationService(mock_db_session)
        await service.update_breach_status(
            breach_id=rec.id, status=BreachStatus.RESOLVED, additional_info="Fixed"
        )
        mock_db_session.commit.assert_awaited()


class TestDeadlineChecking:
    @pytest.mark.asyncio
    async def test_overdue_authority(self, mock_db_session):
        now = datetime.now(timezone.utc)
        b = FakeRecord(detected_at=now - timedelta(hours=80), status="DETECTED")
        mock_db_session.execute.return_value = ok(scalars=[b])
        service = BreachNotificationService(mock_db_session)
        alerts = await service.check_notification_deadlines()
        assert any(a["alert"] == "OVERDUE_AUTHORITY_NOTIFICATION" for a in alerts)

    @pytest.mark.asyncio
    async def test_no_deadline_issues(self, mock_db_session):
        now = datetime.now(timezone.utc)
        b = FakeRecord(detected_at=now - timedelta(hours=1), status="DETECTED")
        mock_db_session.execute.return_value = ok(scalars=[b])
        service = BreachNotificationService(mock_db_session)
        alerts = await service.check_notification_deadlines()
        assert len(alerts) == 0


class TestBreachListing:
    @pytest.mark.asyncio
    async def test_list_by_severity(self, mock_db_session):
        mock_db_session.execute.return_value = ok(scalars=[])
        service = BreachNotificationService(mock_db_session)
        await service.list_breaches(severity=BreachSeverity.CRITICAL)
        mock_db_session.execute.assert_called_once()


class TestBreachEmailTemplates:
    def test_authority_template(self):
        rec = BreachRecord(
            id=uuid4(), fiduciary_id=uuid4(),
            breach_type=BreachType.DATA_EXFILTRATION, severity=BreachSeverity.CRITICAL,
            status=BreachStatus.DETECTED,
            detected_at=datetime.now(timezone.utc) - timedelta(hours=24),
            description="Test breach description.",
            affected_principals_count=500,
            data_categories_involved=["NAME", "EMAIL"],
            containment_measures=["Isolated"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )
        email = BreachNotificationTemplate.authority_notification_email(rec, "DPBI-1234")
        assert "DPBI-1234" in email
        assert "CRITICAL" in email
        assert "500" in email

    def test_principal_template(self):
        rec = BreachRecord(
            id=uuid4(), fiduciary_id=uuid4(),
            breach_type=BreachType.UNAUTHORIZED_ACCESS, severity=BreachSeverity.HIGH,
            status=BreachStatus.DETECTED,
            detected_at=datetime.now(timezone.utc) - timedelta(hours=24),
            description="Unauthorized access detected.",
            affected_principals_count=100,
            data_categories_involved=["NAME"],
            containment_measures=["Locked down"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )
        email = BreachNotificationTemplate.principal_notification_email(rec)
        assert "Unauthorized access" in email


class TestBreachPydanticModels:
    def test_breach_create_valid(self):
        data = BreachCreate(
            fiduciary_id=uuid4(), breach_type=BreachType.PHISHING,
            severity=BreachSeverity.MEDIUM,
            description="Phishing campaign targeted employees requiring password reset.",
            detected_at=datetime.now(timezone.utc),
            affected_principals_count=50,
            data_categories_involved=["EMAIL"],
        )
        assert data.breach_type == BreachType.PHISHING

    def test_breach_update_partial(self):
        u = BreachUpdate(status=BreachStatus.CONTAINED)
        assert u.status == BreachStatus.CONTAINED


class TestBreachEnums:
    def test_severity_levels(self):
        assert BreachSeverity.HIGH.value == "HIGH"
        assert BreachSeverity.CRITICAL.value == "CRITICAL"

    def test_status_values(self):
        assert BreachStatus.DETECTED.value == "DETECTED"
        assert BreachStatus.RESOLVED.value == "RESOLVED"

    def test_breach_types(self):
        assert BreachType.MALWARE.value == "MALWARE"

    def test_deadline_constants(self, mock_db_session):
        s = BreachNotificationService(mock_db_session)
        assert s.AUTHORITY_NOTIFICATION_DEADLINE_HOURS == 72
        assert s.PRINCIPAL_NOTIFICATION_DEADLINE_HOURS == 168
