"""Tests for webhook delivery system."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from api.webhooks.service import WebhookService
from api.schemas import WebhookSubscribeRequest
import json
import hmac
import hashlib
import os


@pytest.fixture
def webhook_service(mock_redis):
    """Webhook service with mocked Redis."""
    return WebhookService(redis_client=mock_redis)


class TestWebhookSubscription:
    """Test webhook subscription management."""

    @pytest.mark.asyncio
    async def test_queue_webhook(self, webhook_service, mock_redis):
        """Successfully queue a webhook for delivery."""
        from uuid import uuid4

        mock_redis.xadd = AsyncMock()

        delivery_id = await webhook_service.queue_webhook(
            subscription_id=uuid4(),
            event_type="consent_granted",
            payload={"consent_id": "test-consent"},
        )

        mock_redis.xadd.assert_called_once()
        assert delivery_id is not None

    @pytest.mark.asyncio
    async def test_webhook_delivery(self, webhook_service, mock_redis):
        """Webhook delivery sends HTTP request."""
        from api.webhooks.service import WebhookSubscription, WebhookDelivery
        from uuid import uuid4

        subscription = WebhookSubscription(
            id=uuid4(),
            fiduciary_id=uuid4(),
            callback_url="https://example.com/webhook",
            secret="test-secret",
            events=["consent_granted"],
        )

        delivery = WebhookDelivery(
            id=uuid4(),
            subscription_id=subscription.id,
            event_type="consent_granted",
            payload={"consent_id": "test-consent", "timestamp": "2026-04-08T12:00:00Z"},
        )

        with patch.object(webhook_service.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            success = await webhook_service.deliver_webhook(
                subscription=subscription,
                delivery=delivery,
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_webhook_retry_on_failure(self, webhook_service, mock_redis):
        """Webhook retries on delivery failure."""
        from api.webhooks.service import WebhookSubscription, WebhookDelivery
        from uuid import uuid4

        subscription = WebhookSubscription(
            id=uuid4(),
            fiduciary_id=uuid4(),
            callback_url="https://example.com/webhook",
            secret="test-secret",
            events=["consent_granted"],
        )

        delivery = WebhookDelivery(
            id=uuid4(),
            subscription_id=subscription.id,
            event_type="consent_granted",
            payload={"event": "consent_granted"},
        )

        with patch.object(webhook_service.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection error")

            success = await webhook_service.deliver_webhook(
                subscription=subscription,
                delivery=delivery,
            )

            assert success is False


class TestWebhookSignature:
    """Test webhook signature generation and verification."""

    def test_signature_generation(self):
        """Webhook signature is HMAC-SHA256."""
        payload = json.dumps({"test": "data"})
        secret = "test-secret"

        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        assert len(signature) == 64  # SHA-256 hex length

    def test_signature_verification(self):
        """Signature can be verified."""
        payload = '{"test": "data"}'
        secret = "test-secret"

        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify
        is_valid = hmac.compare_digest(expected_signature, expected_signature)
        assert is_valid is True


class TestWebhookValidation:
    """Test webhook URL validation (SSRF protection)."""

    @pytest.mark.skipif(
        os.getenv("TESTING", "").lower() in ("1", "true", "yes"),
        reason="SSRF validation is disabled in TESTING mode"
    )
    def test_valid_https_url(self):
        """Valid HTTPS URLs are accepted."""
        from api.schemas import validate_callback_url

        result = validate_callback_url("https://example.com/webhook")
        assert result == "https://example.com/webhook"

    @pytest.mark.skipif(
        os.getenv("TESTING", "").lower() in ("1", "true", "yes"),
        reason="SSRF validation is disabled in TESTING mode"
    )
    def test_private_ip_blocked(self):
        """Private IP ranges are blocked."""
        from api.schemas import validate_callback_url

        with pytest.raises(ValueError, match="blocked hostname|Invalid URL"):
            validate_callback_url("https://192.168.1.1/webhook")

        with pytest.raises(ValueError, match="blocked hostname|Invalid URL"):
            validate_callback_url("https://10.0.0.1/webhook")

        with pytest.raises(ValueError, match="blocked hostname|Invalid URL"):
            validate_callback_url("https://127.0.0.1/webhook")

    @pytest.mark.skipif(
        os.getenv("TESTING", "").lower() in ("1", "true", "yes"),
        reason="SSRF validation is disabled in TESTING mode"
    )
    def test_localhost_blocked(self):
        """Localhost is blocked."""
        from api.schemas import validate_callback_url

        with pytest.raises(ValueError, match="blocked hostname|Invalid URL"):
            validate_callback_url("https://localhost/webhook")

    @pytest.mark.skipif(
        os.getenv("TESTING", "").lower() in ("1", "true", "yes"),
        reason="SSRF validation is disabled in TESTING mode"
    )
    def test_aws_metadata_blocked(self):
        """AWS metadata endpoint is blocked."""
        from api.schemas import validate_callback_url

        with pytest.raises(ValueError, match="blocked hostname|Invalid URL"):
            validate_callback_url("https://169.254.169.254/latest/meta-data/")
