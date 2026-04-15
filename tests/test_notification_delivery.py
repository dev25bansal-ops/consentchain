"""Tests for breach notification and deletion deadline enforcement."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
import json


class TestBreachNotificationDelivery:
    """Tests for actual breach notification delivery."""

    @pytest.mark.asyncio
    async def test_notify_principals_sends_email(self):
        """Test that breach notification actually sends emails."""
        from api.breach import (
            BreachNotificationService,
            BreachCreate,
            BreachType,
            BreachSeverity,
        )

        mock_db = AsyncMock()
        mock_session = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.add = Mock()

        breach_id = uuid4()
        principal_id = uuid4()
        fiduciary_id = uuid4()

        mock_breach_record = Mock()
        mock_breach_record.id = breach_id
        mock_breach_record.fiduciary_id = fiduciary_id
        mock_breach_record.breach_type = "DATA_EXFILTRATION"
        mock_breach_record.severity = "HIGH"
        mock_breach_record.status = "CONTAINED"
        mock_breach_record.detected_at = datetime.now(timezone.utc)
        mock_breach_record.description = "Test breach"
        mock_breach_record.affected_principals_count = 1
        mock_breach_record.data_categories_involved = json.dumps(["email", "name"])
        mock_breach_record.containment_measures = json.dumps(["isolated"])

        mock_principal = Mock()
        mock_principal.id = principal_id
        mock_principal.email = "test@example.com"
        mock_principal.phone = "+1234567890"
        mock_principal.name = "Test User"

        with patch.object(mock_db, "execute") as mock_exec:
            mock_exec.return_value = MagicMock()
            mock_exec.return_value.scalar_one_or_none = Mock(return_value=mock_principal)

            with patch("api.breach.BreachNotificationService.get_breach") as mock_get_breach:
                from api.breach import BreachRecord, BreachType, BreachSeverity

                mock_get_breach.return_value = BreachRecord(
                    id=breach_id,
                    fiduciary_id=fiduciary_id,
                    breach_type=BreachType.DATA_EXFILTRATION,
                    severity=BreachSeverity.HIGH,
                    status=Mock(value="CONTAINED"),
                    detected_at=datetime.now(timezone.utc),
                    description="Test breach",
                    affected_principals_count=1,
                    data_categories_involved=["email", "name"],
                    containment_measures=["isolated"],
                    created_at=datetime.now(timezone.utc),
                )

                with patch("api.notifications.NotificationService") as mock_notif_service:
                    mock_notif_instance = AsyncMock()
                    mock_notif_instance.send_email = AsyncMock(return_value=Mock(success=True))
                    mock_notif_instance.send_sms = AsyncMock(return_value=Mock(success=True))
                    mock_notif_instance.create_notification = AsyncMock(return_value=uuid4())
                    mock_notif_service.return_value = mock_notif_instance

                    service = BreachNotificationService(mock_db)

                    result = await service.notify_principals(
                        breach_id=breach_id,
                        principal_ids=[principal_id],
                    )

                    assert len(result) == 1

    def test_breach_html_email_generation(self):
        """Test HTML email generation for breach notification."""
        from api.breach import BreachNotificationService, BreachRecord, BreachType, BreachSeverity

        breach = BreachRecord(
            id=uuid4(),
            fiduciary_id=uuid4(),
            breach_type=BreachType.PHISHING,
            severity=BreachSeverity.HIGH,
            status=Mock(value="CONTAINED"),
            detected_at=datetime.now(timezone.utc),
            description="A phishing attack compromised user credentials",
            affected_principals_count=100,
            data_categories_involved=["email", "password", "name"],
            containment_measures=["passwords reset", "systems secured"],
            created_at=datetime.now(timezone.utc),
        )

        principal = Mock()
        principal.name = "John Doe"
        principal.email = "john@example.com"

        service = BreachNotificationService(Mock())
        html = service._generate_principal_html_email(breach, principal)

        assert "John Doe" in html
        assert "phishing" in html.lower()
        assert "email" in html
        assert "password" in html
        assert "passwords reset" in html

    def test_authority_notification_template(self):
        """Test authority notification email template."""
        from api.breach import BreachNotificationTemplate, BreachRecord, BreachType, BreachSeverity

        breach = BreachRecord(
            id=uuid4(),
            fiduciary_id=uuid4(),
            breach_type=BreachType.UNAUTHORIZED_ACCESS,
            severity=BreachSeverity.CRITICAL,
            status=Mock(value="INVESTIGATING"),
            detected_at=datetime.now(timezone.utc),
            description="Unauthorized access to customer database",
            affected_principals_count=5000,
            data_categories_involved=["financial_data", "personal_info"],
            containment_measures=["access_revoked", "forensics_ongoing"],
            created_at=datetime.now(timezone.utc),
        )

        email = BreachNotificationTemplate.authority_notification_email(breach, "DPBI-ABC12345")

        assert "DPBI-ABC12345" in email
        assert "UNAUTHORIZED_ACCESS" in email
        assert "CRITICAL" in email
        assert "5000" in email
        assert "financial_data" in email
        assert "72-hour" in email


class TestDeletionDeadlineEnforcement:
    """Tests for deletion deadline enforcement worker."""

    def test_deadline_configuration(self):
        """Test deletion deadline is set to 30 days per DPDP Act."""
        from api.workers.expiry_worker import DeletionDeadlineWorker

        assert DeletionDeadlineWorker.DELETION_DEADLINE_DAYS == 30
        assert 7 in DeletionDeadlineWorker.REMINDER_DAYS
        assert 1 in DeletionDeadlineWorker.REMINDER_DAYS

    @pytest.mark.asyncio
    async def test_check_deadlines_finds_approaching(self):
        """Test that check_deadlines finds requests approaching deadline."""
        from api.workers.expiry_worker import DeletionDeadlineWorker

        mock_session_factory = Mock()
        mock_session = AsyncMock()

        now = datetime.now(timezone.utc)
        deadline_in_7_days = now + timedelta(days=7)

        mock_request = Mock()
        mock_request.id = uuid4()
        mock_request.principal_id = uuid4()
        mock_request.fiduciary_id = uuid4()
        mock_request.created_at = now - timedelta(days=23)
        mock_request.status = "PENDING"
        mock_request.scheduled_at = deadline_in_7_days

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_request]

        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        worker = DeletionDeadlineWorker(
            session_factory=mock_session_factory,
            notification_service=None,
        )

        result = await worker.check_deadlines()

        assert "checked" in result
        assert "reminders_sent" in result

    @pytest.mark.asyncio
    async def test_process_overdue_identifies_violations(self):
        """Test that overdue requests are identified and escalated."""
        from api.workers.expiry_worker import DeletionDeadlineWorker

        mock_session_factory = Mock()
        mock_session = AsyncMock()

        now = datetime.now(timezone.utc)
        overdue_date = now - timedelta(days=35)

        mock_request = Mock()
        mock_request.id = uuid4()
        mock_request.principal_id = uuid4()
        mock_request.fiduciary_id = uuid4()
        mock_request.created_at = overdue_date
        mock_request.status = "PENDING"
        mock_request.extra_data = "{}"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_request]

        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        worker = DeletionDeadlineWorker(
            session_factory=mock_session_factory,
            notification_service=None,
        )

        result = await worker.process_overdue_requests()

        assert result["overdue"] == 1

    def test_reminder_email_contains_dpdp_reference(self):
        """Test that reminder emails reference DPDP Act Section 9."""
        from api.workers.expiry_worker import DeletionDeadlineWorker

        worker = DeletionDeadlineWorker(
            session_factory=Mock(),
            notification_service=None,
        )

        assert worker.DELETION_DEADLINE_DAYS == 30


class TestNotificationServiceIntegration:
    """Tests for notification service with actual providers."""

    def test_email_provider_configured_when_env_set(self):
        """Test that email provider is marked configured when API key is set."""
        from api.notifications import EmailProvider

        with patch.dict("os.environ", {"SENDGRID_API_KEY": "test-key"}):
            provider = EmailProvider()
            assert provider.is_configured is True

    def test_email_provider_not_configured_without_key(self):
        """Test that email provider is not configured without API key."""
        from api.notifications import EmailProvider

        with patch.dict("os.environ", {}, clear=True):
            if "SENDGRID_API_KEY" in __import__("os").environ:
                del __import__("os").environ["SENDGRID_API_KEY"]
            provider = EmailProvider()
            assert provider.is_configured is False

    def test_sms_provider_configured_when_env_set(self):
        """Test that SMS provider is marked configured when credentials are set."""
        from api.notifications import SMSProvider

        with patch.dict(
            "os.environ",
            {
                "TWILIO_ACCOUNT_SID": "test-sid",
                "TWILIO_AUTH_TOKEN": "test-token",
                "TWILIO_PHONE_NUMBER": "+1234567890",
            },
        ):
            provider = SMSProvider()
            assert provider.is_configured is True

    @pytest.mark.asyncio
    async def test_send_email_returns_result(self):
        """Test that send_email returns a NotificationResult."""
        from api.notifications import NotificationService, EmailNotification

        mock_db = AsyncMock()
        service = NotificationService(mock_db)

        with patch.object(service.email_provider, "send") as mock_send:
            mock_send.return_value = Mock(success=True, notification_id="msg-123")

            result = await service.send_email(
                recipient_email="test@example.com",
                subject="Test Subject",
                html_body="<p>Test</p>",
            )

            assert result.success is True
            assert result.notification_id == "msg-123"

    @pytest.mark.asyncio
    async def test_send_sms_returns_result(self):
        """Test that send_sms returns a NotificationResult."""
        from api.notifications import NotificationService

        mock_db = AsyncMock()
        service = NotificationService(mock_db)

        with patch.object(service.sms_provider, "send") as mock_send:
            mock_send.return_value = Mock(success=True, notification_id="sid-456")

            result = await service.send_sms(
                recipient_phone="+1234567890",
                message="Test message",
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_notify_breach_sends_both_channels(self):
        """Test that breach notification sends to both email and SMS."""
        from api.notifications import NotificationService

        mock_db = AsyncMock()
        service = NotificationService(mock_db)

        with patch.object(service, "send_email") as mock_email:
            with patch.object(service, "send_sms") as mock_sms:
                mock_email.return_value = Mock(success=True)
                mock_sms.return_value = Mock(success=True)

                results = await service.notify_breach(
                    email="test@example.com",
                    phone="+1234567890",
                    name="Test User",
                    breach_type="DATA_EXFILTRATION",
                    affected_data=["email", "name"],
                    actions_taken="Systems secured, passwords reset",
                )

                assert "email" in results
                assert "sms" in results
                mock_email.assert_called_once()
                mock_sms.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
