"""Tests for Mobile SDK support.

Covers:
- Device registration and unregistration
- Push token management
- Push notification sending (APNs, FCM)
- Deep link generation and parsing
- Multi-device management per user
- Platform-specific payload building
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from api.mobile import (
    mobile_sdk_support,
    MobileSDKSupport,
    MobileDevice,
    MobilePlatform,
    NotificationType,
    PushNotification,
    DeepLink,
    SDKConfig,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fresh_mobile():
    """Provide a fresh MobileSDKSupport instance."""
    return MobileSDKSupport()


@pytest.fixture
def ios_device():
    """Provide an iOS mobile device."""
    return MobileDevice(
        device_id="ios-device-001",
        platform=MobilePlatform.IOS,
        push_token="apns-token-abc123def456",
        app_version="2.0.0",
        os_version="17.0",
        notification_enabled=True,
        biometric_enabled=True,
    )


@pytest.fixture
def android_device():
    """Provide an Android mobile device."""
    return MobileDevice(
        device_id="android-device-001",
        platform=MobilePlatform.ANDROID,
        push_token="fcm-token-xyz789",
        app_version="2.0.0",
        os_version="14",
        notification_enabled=True,
        biometric_enabled=False,
    )


@pytest.fixture
def consent_notification():
    """Provide a consent request notification."""
    return PushNotification(
        title="New Consent Request",
        body="A company is requesting your consent to process personal data.",
        notification_type=NotificationType.CONSENT_REQUEST,
        data={"consent_id": "consent-123", "fiduciary": "Test Corp"},
        sound="default",
        badge=1,
    )


# ============================================================
# Test: Device Registration
# ============================================================


class TestDeviceRegistration:
    """Test mobile device registration."""

    def test_register_ios_device(self, fresh_mobile, ios_device):
        """iOS device registers successfully."""
        result = fresh_mobile.register_device("user-001", ios_device)

        assert result["success"] is True
        assert result["device_id"] == "ios-device-001"
        assert "registered_at" in result
        assert result["features"]["push_notifications"] is True
        assert result["features"]["biometric_auth"] is True

    def test_register_android_device(self, fresh_mobile, android_device):
        """Android device registers successfully."""
        result = fresh_mobile.register_device("user-002", android_device)

        assert result["success"] is True
        assert result["features"]["push_notifications"] is True
        assert result["features"]["biometric_auth"] is False

    def test_register_device_without_push_token(self, fresh_mobile):
        """Device without push token registers but notifications disabled."""
        device = MobileDevice(
            device_id="device-no-push",
            platform=MobilePlatform.IOS,
        )
        result = fresh_mobile.register_device("user-003", device)

        assert result["success"] is True
        assert result["features"]["push_notifications"] is False

    def test_register_multiple_devices_same_user(self, fresh_mobile, ios_device, android_device):
        """User can register multiple devices."""
        fresh_mobile.register_device("user-001", ios_device)
        fresh_mobile.register_device("user-001", android_device)

        devices = fresh_mobile.get_user_devices("user-001")
        assert len(devices) == 2
        device_ids = [d.device_id for d in devices]
        assert "ios-device-001" in device_ids
        assert "android-device-001" in device_ids

    def test_register_duplicate_device_id(self, fresh_mobile, ios_device):
        """Duplicate device ID overwrites existing registration."""
        fresh_mobile.register_device("user-001", ios_device)
        result = fresh_mobile.register_device("user-002", ios_device)

        assert result["success"] is True
        # Device should now be associated with user-002 only
        devices_001 = fresh_mobile.get_user_devices("user-001")
        devices_002 = fresh_mobile.get_user_devices("user-002")
        assert len(devices_002) == 1


# ============================================================
# Test: Device Unregistration
# ============================================================


class TestDeviceUnregistration:
    """Test mobile device unregistration."""

    def test_unregister_device(self, fresh_mobile, ios_device):
        """Device can be unregistered."""
        fresh_mobile.register_device("user-001", ios_device)

        result = fresh_mobile.unregister_device("ios-device-001")

        assert result is True
        devices = fresh_mobile.get_user_devices("user-001")
        assert len(devices) == 0

    def test_unregister_nonexistent_device(self, fresh_mobile):
        """Unregistering nonexistent device returns False."""
        assert fresh_mobile.unregister_device("nonexistent-device") is False

    def test_unregister_removes_from_user_devices(self, fresh_mobile, ios_device):
        """Unregistering removes device from user's device list."""
        fresh_mobile.register_device("user-001", ios_device)
        fresh_mobile.unregister_device("ios-device-001")

        devices = fresh_mobile.get_user_devices("user-001")
        assert "ios-device-001" not in [d.device_id for d in devices]


# ============================================================
# Test: Push Token Management
# ============================================================


class TestPushTokenManagement:
    """Test push token updates."""

    def test_update_push_token(self, fresh_mobile, ios_device):
        """Push token can be updated."""
        fresh_mobile.register_device("user-001", ios_device)

        result = fresh_mobile.update_push_token("ios-device-001", "new-apns-token")

        assert result is True
        device = fresh_mobile._devices["ios-device-001"]
        assert device.push_token == "new-apns-token"

    def test_update_push_token_nonexistent_device(self, fresh_mobile):
        """Updating token for nonexistent device returns False."""
        assert fresh_mobile.update_push_token("nonexistent", "new-token") is False


# ============================================================
# Test: Push Notifications
# ============================================================


class TestPushNotifications:
    """Test push notification delivery."""

    @pytest.mark.asyncio
    async def test_send_notification_ios(self, fresh_mobile, ios_device, consent_notification):
        """Notification sent to iOS device."""
        fresh_mobile.register_device("user-001", ios_device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
        )

        assert result["total"] == 1
        assert result["sent"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_notification_android(self, fresh_mobile, android_device, consent_notification):
        """Notification sent to Android device."""
        fresh_mobile.register_device("user-001", android_device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
        )

        assert result["total"] == 1
        assert result["sent"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_notification_no_devices(self, fresh_mobile, consent_notification):
        """Sending to user with no devices returns zero sent."""
        result = await fresh_mobile.send_push_notification(
            user_id="nonexistent-user",
            notification=consent_notification,
        )

        assert result["total"] == 0
        assert result["sent"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_notification_disabled_device(self, fresh_mobile, consent_notification):
        """Notification skipped for device with notifications disabled."""
        device = MobileDevice(
            device_id="disabled-device",
            platform=MobilePlatform.IOS,
            push_token="some-token",
            notification_enabled=False,
        )
        fresh_mobile.register_device("user-001", device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
        )

        assert result["total"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_send_notification_no_push_token(self, fresh_mobile, consent_notification):
        """Notification skipped for device without push token."""
        device = MobileDevice(
            device_id="no-token-device",
            platform=MobilePlatform.ANDROID,
            notification_enabled=True,
        )
        fresh_mobile.register_device("user-001", device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
        )

        assert result["total"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_send_to_specific_devices(self, fresh_mobile, ios_device, android_device, consent_notification):
        """Notification sent only to specified devices."""
        fresh_mobile.register_device("user-001", ios_device)
        fresh_mobile.register_device("user-001", android_device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
            devices=["ios-device-001"],
        )

        assert result["total"] == 1
        assert result["sent"] == 1

    @pytest.mark.asyncio
    async def test_send_notification_multiple_devices(self, fresh_mobile, ios_device, android_device, consent_notification):
        """Notification sent to all user devices."""
        fresh_mobile.register_device("user-001", ios_device)
        fresh_mobile.register_device("user-001", android_device)

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=consent_notification,
        )

        assert result["total"] == 2
        assert result["sent"] == 2


# ============================================================
# Test: Platform Payload Building
# ============================================================


class TestPayloadBuilding:
    """Test platform-specific notification payload building."""

    def test_ios_payload(self, fresh_mobile, consent_notification):
        """iOS payload has aps structure."""
        device = MobileDevice(
            device_id="ios-device",
            platform=MobilePlatform.IOS,
            push_token="token",
        )
        payload = fresh_mobile._build_payload(MobilePlatform.IOS, consent_notification)

        assert "aps" in payload
        assert payload["aps"]["alert"]["title"] == "New Consent Request"
        assert payload["aps"]["sound"] == "default"
        assert payload["aps"]["badge"] == 1
        assert payload["data"]["type"] == "consent_request"

    def test_android_payload(self, fresh_mobile, consent_notification):
        """Android payload has notification structure."""
        payload = fresh_mobile._build_payload(MobilePlatform.ANDROID, consent_notification)

        assert "notification" in payload
        assert payload["notification"]["title"] == "New Consent Request"
        assert payload["data"]["type"] == "consent_request"
        assert "android" in payload


# ============================================================
# Test: Deep Links
# ============================================================


class TestDeepLinks:
    """Test deep link generation and parsing."""

    def test_generate_simple_deep_link(self, fresh_mobile):
        """Simple deep link without params."""
        link = fresh_mobile.generate_deep_link("consent/view")

        assert link.startswith("consentchain://")
        assert "consent/view" in link

    def test_generate_deep_link_with_params(self, fresh_mobile):
        """Deep link with query parameters."""
        link = fresh_mobile.generate_deep_link(
            path="consent/view",
            params={"id": "123", "action": "review"},
        )

        assert "id=123" in link
        assert "action=review" in link

    def test_generate_deep_link_with_source(self, fresh_mobile):
        """Deep link with source tracking."""
        link = fresh_mobile.generate_deep_link(
            path="consent/view",
            params={"id": "123"},
            source="email_campaign",
        )

        assert "source=email_campaign" in link

    def test_parse_deep_link(self, fresh_mobile):
        """Deep link parsing extracts path, params, and source."""
        url = "consentchain://consent/view?id=123&action=review&source=email"
        parsed = fresh_mobile.parse_deep_link(url)

        assert parsed is not None
        assert parsed.path == "consent/view"
        assert parsed.params["id"] == "123"
        assert parsed.params["action"] == "review"
        assert parsed.source == "email"

    def test_parse_deep_link_no_params(self, fresh_mobile):
        """Deep link without params parses correctly."""
        url = "consentchain://home"
        parsed = fresh_mobile.parse_deep_link(url)

        assert parsed is not None
        assert parsed.path == "home"
        assert parsed.params == {}
        assert parsed.source is None

    def test_parse_invalid_url(self, fresh_mobile):
        """Non-consentchain URL returns None."""
        parsed = fresh_mobile.parse_deep_link("https://example.com/consent/view")
        assert parsed is None

    def test_parse_deep_link_only_source(self, fresh_mobile):
        """Deep link with only source param."""
        url = "consentchain://dashboard?source=push"
        parsed = fresh_mobile.parse_deep_link(url)

        assert parsed.path == "dashboard"
        assert parsed.source == "push"


# ============================================================
# Test: Get User Devices
# ============================================================


class TestGetUserDevices:
    """Test retrieving devices for a user."""

    def test_get_devices_for_user(self, fresh_mobile, ios_device, android_device):
        """All devices for a user are returned."""
        fresh_mobile.register_device("user-001", ios_device)
        fresh_mobile.register_device("user-001", android_device)

        devices = fresh_mobile.get_user_devices("user-001")

        assert len(devices) == 2
        assert any(d.platform == MobilePlatform.IOS for d in devices)
        assert any(d.platform == MobilePlatform.ANDROID for d in devices)

    def test_get_devices_no_user(self, fresh_mobile):
        """Empty list for user with no devices."""
        assert fresh_mobile.get_user_devices("nonexistent") == []

    def test_device_last_active(self, fresh_mobile, ios_device):
        """Device tracks last active timestamp."""
        fresh_mobile.register_device("user-001", ios_device)
        devices = fresh_mobile.get_user_devices("user-001")

        assert devices[0].last_active is not None
        assert isinstance(devices[0].last_active, datetime)


# ============================================================
# Test: Notification Types
# ============================================================


class TestNotificationTypes:
    """Test all notification types are supported."""

    def test_all_notification_types(self):
        """All notification type enum values exist."""
        assert NotificationType.CONSENT_REQUEST.value == "consent_request"
        assert NotificationType.CONSENT_GRANTED.value == "consent_granted"
        assert NotificationType.CONSENT_REVOKED.value == "consent_revoked"
        assert NotificationType.CONSENT_EXPIRING.value == "consent_expiring"
        assert NotificationType.BREACH_ALERT.value == "breach_alert"
        assert NotificationType.DELETION_COMPLETED.value == "deletion_completed"

    @pytest.mark.asyncio
    async def test_breach_alert_notification(self, fresh_mobile, ios_device):
        """Breach alert notification can be sent."""
        fresh_mobile.register_device("user-001", ios_device)

        notification = PushNotification(
            title="Security Alert",
            body="A data breach has been detected affecting your account.",
            notification_type=NotificationType.BREACH_ALERT,
            data={"breach_id": "breach-123"},
        )

        result = await fresh_mobile.send_push_notification(
            user_id="user-001",
            notification=notification,
        )

        assert result["sent"] == 1
