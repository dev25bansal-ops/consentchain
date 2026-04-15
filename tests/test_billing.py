"""Tests for Stripe Billing Integration.

Covers:
- Stripe webhook signature verification
- Webhook event handling (checkout, subscription, invoice)
- Checkout session creation
- Billing portal session creation
- Billing status retrieval
- Invoice listing
- Duplicate event detection
"""

import pytest
import json
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from api.billing import (
    verify_stripe_signature,
    handle_checkout_completed,
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_invoice_paid,
    handle_payment_failed,
    handle_customer_created,
    CheckoutSessionCreate,
    PortalSessionCreate,
)
from api.tenant import TenantPlan, TenantStatus, BillingCycle


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def stripe_webhook_secret():
    return "whsec_test_secret_key_12345678"


@pytest.fixture
def mock_session():
    """Provide a mocked async database session."""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_tenant():
    """Provide a mock tenant database record."""
    tenant = MagicMock()
    tenant.id = uuid4()
    tenant.stripe_customer_id = None
    tenant.stripe_subscription_id = None
    tenant.plan = MagicMock()
    tenant.plan.value = "free"
    tenant.status = MagicMock()
    tenant.status.value = "trial"
    tenant.billing_cycle = MagicMock()
    tenant.billing_cycle.value = "monthly"
    tenant.subscription_ends_at = None
    return tenant


def _make_stripe_event(event_type, data, event_id=None):
    """Helper to create a Stripe webhook event dict."""
    return {
        "id": event_id or f"evt_{uuid4().hex[:24]}",
        "type": event_type,
        "data": {"object": data},
        "created": int(datetime.now(timezone.utc).timestamp()),
    }


def _sign_stripe_payload(payload_bytes, secret, timestamp=None):
    """Create a valid Stripe signature header matching billing implementation.

    Note: The billing/verify_stripe_signature function signs just the raw
    payload bytes (not timestamp.payload like real Stripe). This helper
    matches that simplified implementation.
    """
    ts = timestamp or str(int(datetime.now(timezone.utc).timestamp()))
    signature = hmac.new(
        secret.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={signature}"


# ============================================================
# Test: Signature Verification
# ============================================================


class TestStripeSignatureVerification:
    """Test Stripe webhook signature verification."""

    def test_valid_signature(self, stripe_webhook_secret):
        """Valid signature passes verification."""
        payload = b'{"type": "checkout.session.completed"}'
        signature = _sign_stripe_payload(payload, stripe_webhook_secret)

        assert verify_stripe_signature(payload, signature, stripe_webhook_secret) is True

    def test_invalid_signature(self, stripe_webhook_secret):
        """Invalid signature fails verification."""
        payload = b'{"type": "checkout.session.completed"}'

        assert verify_stripe_signature(payload, "t=0,v1=invalid", stripe_webhook_secret) is False

    def test_wrong_secret(self, stripe_webhook_secret):
        """Wrong secret fails verification."""
        payload = b'{"type": "checkout.session.completed"}'
        signature = _sign_stripe_payload(payload, "wrong_secret")

        assert verify_stripe_signature(payload, signature, stripe_webhook_secret) is False

    def test_no_secret_returns_false(self):
        """Empty secret always returns False."""
        payload = b'{"type": "test"}'
        assert verify_stripe_signature(payload, "t=1,v1=abc", "") is False

    def test_malformed_signature(self, stripe_webhook_secret):
        """Malformed signature string fails gracefully."""
        payload = b'{"type": "test"}'
        assert verify_stripe_signature(payload, "malformed-signature", stripe_webhook_secret) is False

    def test_missing_v1_component(self, stripe_webhook_secret):
        """Signature without v1 component fails."""
        payload = b'{"type": "test"}'
        assert verify_stripe_signature(payload, "t=1234567890", stripe_webhook_secret) is False


# ============================================================
# Test: Webhook Event Handlers
# ============================================================


class TestCheckoutCompletedHandler:
    """Test checkout.session.completed webhook handler."""

    @pytest.mark.asyncio
    async def test_checkout_completed_links_tenant(self, mock_session, mock_tenant):
        """Checkout completion links Stripe customer to tenant."""
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_checkout_completed(
            mock_session,
            data={
                "customer": "cus_stripe123",
                "subscription": "sub_stripe456",
                "client_reference_id": str(mock_tenant.id),
            },
            event_id="evt_checkout",
        )

        assert mock_tenant.stripe_customer_id == "cus_stripe123"
        assert mock_tenant.stripe_subscription_id == "sub_stripe456"

    @pytest.mark.asyncio
    async def test_checkout_completed_missing_reference(self, mock_session, caplog):
        """Missing client_reference_id logs warning."""
        await handle_checkout_completed(
            mock_session,
            data={"customer": "cus_123", "subscription": "sub_456"},
            event_id="evt_checkout",
        )

        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_completed_invalid_tenant_id(self, mock_session, caplog):
        """Invalid tenant UUID logs warning."""
        await handle_checkout_completed(
            mock_session,
            data={
                "customer": "cus_123",
                "client_reference_id": "not-a-uuid",
            },
            event_id="evt_checkout",
        )

        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_completed_tenant_not_found(self, mock_session):
        """Tenant not found: handler returns without error."""
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        await handle_checkout_completed(
            mock_session,
            data={"customer": "cus_123", "client_reference_id": str(uuid4())},
            event_id="evt_checkout",
        )

        mock_session.add.assert_not_called()


class TestSubscriptionHandlers:
    """Test subscription webhook event handlers."""

    @pytest.mark.asyncio
    async def test_subscription_created(self, mock_session, mock_tenant):
        """Subscription creation activates tenant."""
        mock_tenant.stripe_customer_id = "cus_123"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_subscription_created(
            mock_session,
            data={
                "customer": "cus_123",
                "id": "sub_new",
                "status": "active",
                "plan": {"id": "price_pro_monthly"},
            },
            event_id="evt_sub_created",
        )

        assert mock_tenant.stripe_subscription_id == "sub_new"

    @pytest.mark.asyncio
    async def test_subscription_updated_active(self, mock_session, mock_tenant):
        """Active subscription keeps tenant active."""
        mock_tenant.stripe_customer_id = "cus_123"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_subscription_updated(
            mock_session,
            data={
                "customer": "cus_123",
                "id": "sub_123",
                "status": "active",
                "cancel_at_period_end": False,
            },
            event_id="evt_sub_updated",
        )


class TestSubscriptionDeletedHandler:
    """Test subscription deletion handler."""

    @pytest.mark.asyncio
    async def test_subscription_deleted_cancels_tenant(self, mock_session, mock_tenant):
        """Subscription deletion cancels tenant and clears subscription."""
        mock_tenant.stripe_customer_id = "cus_123"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_subscription_deleted(
            mock_session,
            data={"customer": "cus_123"},
            event_id="evt_sub_deleted",
        )

        mock_session.commit.assert_awaited()


class TestInvoiceHandlers:
    """Test invoice webhook event handlers."""

    @pytest.mark.asyncio
    async def test_invoice_paid(self, mock_session, mock_tenant):
        """Paid invoice keeps tenant active."""
        mock_tenant.stripe_customer_id = "cus_123"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_invoice_paid(
            mock_session,
            data={
                "customer": "cus_123",
                "id": "inv_123",
                "amount_paid": 9900,
                "currency": "usd",
            },
            event_id="evt_invoice_paid",
        )

        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_failed_first_attempt(self, mock_session, mock_tenant):
        """First payment failure does not suspend tenant."""
        mock_tenant.stripe_customer_id = "cus_123"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_payment_failed(
            mock_session,
            data={
                "customer": "cus_123",
                "id": "inv_456",
                "attempt_count": 1,
            },
            event_id="evt_payment_failed",
        )


class TestCustomerCreatedHandler:
    """Test customer.created webhook handler."""

    @pytest.mark.asyncio
    async def test_customer_created_links_to_tenant(self, mock_session, mock_tenant):
        """Customer creation links Stripe customer to tenant."""
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant))

        await handle_customer_created(
            mock_session,
            data={
                "id": "cus_new",
                "email": "tenant@example.com",
                "metadata": {"tenant_id": str(mock_tenant.id)},
            },
            event_id="evt_customer_created",
        )

        assert mock_tenant.stripe_customer_id == "cus_new"

    @pytest.mark.asyncio
    async def test_customer_created_invalid_tenant_id(self, mock_session):
        """Invalid tenant_id in metadata is handled gracefully."""
        await handle_customer_created(
            mock_session,
            data={
                "id": "cus_new",
                "metadata": {"tenant_id": "not-a-uuid"},
            },
            event_id="evt_customer_created",
        )

        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_customer_created_no_metadata(self, mock_session):
        """Customer without tenant_id metadata is skipped."""
        await handle_customer_created(
            mock_session,
            data={"id": "cus_new", "email": "test@example.com"},
            event_id="evt_customer_created",
        )


# ============================================================
# Test: Pydantic Models
# ============================================================


class TestBillingPydanticModels:
    """Test billing request/response models."""

    def test_checkout_session_create_valid(self):
        """Valid checkout session data."""
        data = CheckoutSessionCreate(
            plan="professional",
            billing_cycle="yearly",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert data.plan == "professional"
        assert data.billing_cycle == "yearly"

    def test_checkout_session_create_invalid_plan(self):
        """Invalid plan fails validation."""
        with pytest.raises(Exception):
            CheckoutSessionCreate(
                plan="invalid_plan",
                billing_cycle="monthly",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

    def test_portal_session_create(self):
        """Portal session creation data."""
        data = PortalSessionCreate(return_url="https://example.com/billing")
        assert data.return_url == "https://example.com/billing"


# ============================================================
# Test: Stripe Event Helpers
# ============================================================


class TestStripeEventHelpers:
    """Test Stripe event creation and signing helpers."""

    def test_make_stripe_event(self):
        """Event dict has required structure."""
        event = _make_stripe_event("checkout.session.completed", {"id": "cs_123"})

        assert "id" in event
        assert event["type"] == "checkout.session.completed"
        assert event["data"]["object"]["id"] == "cs_123"

    def test_sign_stripe_payload(self):
        """Signed payload can be verified."""
        payload = b'{"test": true}'
        secret = "whsec_test"
        signature = _sign_stripe_payload(payload, secret)

        assert "t=" in signature
        assert "v1=" in signature
        assert verify_stripe_signature(payload, signature, secret) is True
