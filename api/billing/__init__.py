"""Stripe Billing Integration for Multi-Tenant SaaS.

Provides:
- Stripe webhook handling
- Customer/subscription management
- Invoice and payment tracking
- Usage-based billing support
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
import json
import logging
import os
import hashlib
import hmac

from pydantic import BaseModel, Field

from api.database import (
    TenantDB,
    BillingEventDB,
    TenantPlanDB,
    TenantStatusDB,
    BillingCycleDB,
)
from api.tenant import TenantPlan, PLAN_LIMITS, PLAN_PRICING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_ENABLED = bool(STRIPE_API_KEY)


class CheckoutSessionCreate(BaseModel):
    plan: str = Field(..., pattern="^(starter|professional|enterprise)$")
    billing_cycle: str = Field("monthly", pattern="^(monthly|yearly)$")
    success_url: str
    cancel_url: str


class PortalSessionCreate(BaseModel):
    return_url: str


class BillingStatusResponse(BaseModel):
    tenant_id: str
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    plan: str
    status: str
    billing_cycle: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    if not secret:
        return False

    try:
        elements = signature.split(",")
        signature_dict = {}
        for element in elements:
            key, value = element.split("=")
            signature_dict[key] = value

        expected_signature = signature_dict.get("v1")
        if not expected_signature:
            return False

        signed_payload = payload
        expected_sig = hmac.new(
            secret.encode(),
            msg=signed_payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, expected_sig)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET and not verify_stripe_signature(
        payload, signature, STRIPE_WEBHOOK_SECRET
    ):
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})
    event_id = event.get("id", "")

    session = request.state.session

    existing = await session.execute(
        select(BillingEventDB).where(BillingEventDB.stripe_event_id == event_id)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Webhook event already processed: {event_id}")
        return {"received": True}

    handler_map = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.created": handle_subscription_created,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_payment_failed,
        "customer.created": handle_customer_created,
    }

    handler = handler_map.get(event_type)
    if handler:
        try:
            await handler(session, event_data, event_id)
        except Exception as e:
            logger.error(f"Error handling webhook {event_type}: {e}")
            billing_event = BillingEventDB(
                id=uuid4(),
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                event_type=event_type,
                stripe_event_id=event_id,
                status="error",
                extra_data=json.dumps({"error": str(e), "data": event_data}),
            )
            session.add(billing_event)
            await session.commit()
            raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"received": True}


async def handle_checkout_completed(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle successful checkout session."""
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    client_reference_id = data.get("client_reference_id")

    if not client_reference_id:
        logger.warning("No client_reference_id in checkout session")
        return

    try:
        tenant_id = UUID(client_reference_id)
    except ValueError:
        logger.warning(f"Invalid tenant ID in checkout: {client_reference_id}")
        return

    result = await session.execute(select(TenantDB).where(TenantDB.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found: {tenant_id}")
        return

    tenant.stripe_customer_id = customer_id
    tenant.stripe_subscription_id = subscription_id
    tenant.status = TenantStatusDB.ACTIVE

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="checkout_completed",
        stripe_event_id=event_id,
        status="completed",
        extra_data=json.dumps(
            {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            }
        ),
    )
    session.add(billing_event)

    await session.commit()

    logger.info(f"Checkout completed for tenant {tenant_id}")


async def handle_subscription_created(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle subscription creation."""
    customer_id = data.get("customer")
    subscription_id = data.get("id")
    status = data.get("status")
    plan_id = data.get("plan", {}).get("id")

    result = await session.execute(
        select(TenantDB).where(TenantDB.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for customer: {customer_id}")
        return

    tenant.stripe_subscription_id = subscription_id
    tenant.status = TenantStatusDB.ACTIVE

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="subscription_created",
        stripe_event_id=event_id,
        status="completed",
        extra_data=json.dumps(
            {
                "subscription_id": subscription_id,
                "status": status,
            }
        ),
    )
    session.add(billing_event)

    await session.commit()

    logger.info(f"Subscription created for tenant {tenant.id}")


async def handle_subscription_updated(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle subscription updates."""
    customer_id = data.get("customer")
    subscription_id = data.get("id")
    status = data.get("status")
    cancel_at_period_end = data.get("cancel_at_period_end", False)

    result = await session.execute(
        select(TenantDB).where(TenantDB.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for customer: {customer_id}")
        return

    if status == "canceled":
        tenant.status = TenantStatusDB.CANCELLED
    elif status == "past_due":
        tenant.status = TenantStatusDB.SUSPENDED
    elif status == "active":
        tenant.status = TenantStatusDB.ACTIVE

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="subscription_updated",
        stripe_event_id=event_id,
        status="completed",
        extra_data=json.dumps(
            {
                "subscription_id": subscription_id,
                "status": status,
                "cancel_at_period_end": cancel_at_period_end,
            }
        ),
    )
    session.add(billing_event)

    await session.commit()

    logger.info(f"Subscription updated for tenant {tenant.id}: {status}")


async def handle_subscription_deleted(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle subscription deletion."""
    customer_id = data.get("customer")

    result = await session.execute(
        select(TenantDB).where(TenantDB.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for customer: {customer_id}")
        return

    tenant.status = TenantStatusDB.CANCELLED
    tenant.plan = TenantPlanDB.FREE
    tenant.stripe_subscription_id = None

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="subscription_cancelled",
        stripe_event_id=event_id,
        status="completed",
    )
    session.add(billing_event)

    await session.commit()

    logger.info(f"Subscription cancelled for tenant {tenant.id}")


async def handle_invoice_paid(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle successful invoice payment."""
    customer_id = data.get("customer")
    invoice_id = data.get("id")
    amount_paid = data.get("amount_paid", 0)
    currency = data.get("currency", "usd")

    result = await session.execute(
        select(TenantDB).where(TenantDB.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for customer: {customer_id}")
        return

    tenant.status = TenantStatusDB.ACTIVE

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="invoice_paid",
        stripe_event_id=event_id,
        amount=amount_paid,
        currency=currency,
        status="completed",
        extra_data=json.dumps({"invoice_id": invoice_id}),
    )
    session.add(billing_event)

    await session.commit()

    logger.info(f"Invoice paid for tenant {tenant.id}: {amount_paid} {currency}")


async def handle_payment_failed(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle failed payment."""
    customer_id = data.get("customer")
    invoice_id = data.get("id")
    attempt_count = data.get("attempt_count", 0)

    result = await session.execute(
        select(TenantDB).where(TenantDB.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for customer: {customer_id}")
        return

    if attempt_count >= 3:
        tenant.status = TenantStatusDB.SUSPENDED

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="payment_failed",
        stripe_event_id=event_id,
        status="failed",
        extra_data=json.dumps(
            {
                "invoice_id": invoice_id,
                "attempt_count": attempt_count,
            }
        ),
    )
    session.add(billing_event)

    await session.commit()

    logger.warning(f"Payment failed for tenant {tenant.id}, attempt {attempt_count}")


async def handle_customer_created(
    session: AsyncSession,
    data: Dict[str, Any],
    event_id: str,
):
    """Handle customer creation."""
    customer_id = data.get("id")
    email = data.get("email")
    metadata = data.get("metadata", {})
    tenant_id = metadata.get("tenant_id")

    if tenant_id:
        try:
            uuid = UUID(tenant_id)
            result = await session.execute(select(TenantDB).where(TenantDB.id == uuid))
            tenant = result.scalar_one_or_none()

            if tenant:
                tenant.stripe_customer_id = customer_id
                await session.commit()
                logger.info(f"Linked customer {customer_id} to tenant {tenant_id}")
        except ValueError:
            logger.warning(f"Invalid tenant_id in customer metadata: {tenant_id}")


@router.post("/{tenant_id}/checkout", response_model=dict)
async def create_checkout_session(
    tenant_id: str,
    checkout_data: CheckoutSessionCreate,
    request: Request,
):
    """Create a Stripe checkout session for plan upgrade."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe billing not configured")

    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan = TenantPlan(checkout_data.plan)
    pricing = PLAN_PRICING.get(plan, {})
    amount = pricing.get(checkout_data.billing_cycle, 0) * 100

    if amount == 0:
        tenant.plan = TenantPlanDB(plan.value)
        tenant.status = TenantStatusDB.ACTIVE
        await session.commit()

        return {
            "success": True,
            "message": "Plan activated (free plan)",
            "data": {"plan": plan.value, "amount": 0},
        }

    mock_session_id = f"cs_mock_{uuid4().hex[:24]}"

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="checkout_initiated",
        amount=int(amount),
        currency="usd",
        status="pending",
        extra_data=json.dumps(
            {
                "plan": plan.value,
                "billing_cycle": checkout_data.billing_cycle,
                "session_id": mock_session_id,
            }
        ),
    )
    session.add(billing_event)
    await session.commit()

    return {
        "success": True,
        "message": "Checkout session created",
        "data": {
            "session_id": mock_session_id,
            "amount": amount,
            "currency": "usd",
            "plan": plan.value,
            "billing_cycle": checkout_data.billing_cycle,
        },
    }


@router.post("/{tenant_id}/portal", response_model=dict)
async def create_portal_session(
    tenant_id: str,
    portal_data: PortalSessionCreate,
    request: Request,
):
    """Create a Stripe billing portal session."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe billing not configured")

    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer associated")

    mock_portal_url = f"https://billing.consentchain.io/portal/{tenant.stripe_customer_id}"

    return {
        "success": True,
        "message": "Portal session created",
        "data": {
            "url": mock_portal_url,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    }


@router.get("/{tenant_id}/status", response_model=dict)
async def get_billing_status(
    tenant_id: str,
    request: Request,
):
    """Get billing status for a tenant."""
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    billing_events = await session.execute(
        select(BillingEventDB)
        .where(BillingEventDB.tenant_id == tenant.id)
        .order_by(BillingEventDB.created_at.desc())
        .limit(10)
    )
    events = billing_events.scalars().all()

    return {
        "success": True,
        "message": "Billing status retrieved",
        "data": {
            "tenant_id": str(tenant.id),
            "stripe_customer_id": tenant.stripe_customer_id,
            "stripe_subscription_id": tenant.stripe_subscription_id,
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "billing_cycle": tenant.billing_cycle.value,
            "subscription_ends_at": tenant.subscription_ends_at.isoformat()
            if tenant.subscription_ends_at
            else None,
            "recent_events": [
                {
                    "id": str(e.id),
                    "type": e.event_type,
                    "amount": e.amount,
                    "currency": e.currency,
                    "status": e.status,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
        },
    }


@router.get("/{tenant_id}/invoices", response_model=dict)
async def list_invoices(
    tenant_id: str,
    request: Request,
    limit: int = 20,
):
    """List invoices for a tenant."""
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    billing_events = await session.execute(
        select(BillingEventDB)
        .where(
            BillingEventDB.tenant_id == tenant.id,
            BillingEventDB.event_type.in_(["invoice_paid", "payment_failed"]),
        )
        .order_by(BillingEventDB.created_at.desc())
        .limit(limit)
    )
    events = billing_events.scalars().all()

    return {
        "success": True,
        "message": f"Found {len(events)} invoices",
        "data": {
            "invoices": [
                {
                    "id": str(e.id),
                    "type": e.event_type,
                    "amount": e.amount,
                    "currency": e.currency,
                    "status": "paid" if e.event_type == "invoice_paid" else "failed",
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
        },
    }
