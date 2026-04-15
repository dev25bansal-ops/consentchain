"""Tenant Management API Routes.

Provides REST API endpoints for:
- Tenant CRUD operations
- Plan upgrades/downgrades
- Usage tracking and quota checks
- Team member management
- Billing integration (Stripe webhooks)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
import json
import logging
import os

from pydantic import BaseModel, Field

from api.database import (
    TenantDB,
    TenantMemberDB,
    UsageRecordDB,
    BillingEventDB,
    TenantPlanDB,
    TenantStatusDB,
    BillingCycleDB,
)
from api.tenant import (
    TenantPlan,
    TenantStatus,
    BillingCycle,
    PLAN_LIMITS,
    PLAN_PRICING,
    TenantCreate,
    TenantUpdate,
    PlanUpgrade,
    TenantResponse,
    UsageResponse,
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/api/v1/tenant", tags=["tenant"])


class UsageRecordCreate(BaseModel):
    resource_type: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(1, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class MemberInvite(BaseModel):
    user_id: UUID
    role: str = Field("member", pattern="^(owner|admin|member|viewer)$")


class MemberUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(owner|admin|member|viewer)$")
    is_active: Optional[bool] = None


class BillingPortalResponse(BaseModel):
    url: str
    expires_at: str


async def get_tenant_from_header(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TenantDB:
    token = credentials.credentials
    tenant_id = request.headers.get("X-Tenant-ID")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


@router.post("", response_model=dict)
async def create_tenant(
    request: Request,
    tenant_data: TenantCreate,
):
    session = request.state.session

    existing = await session.execute(select(TenantDB).where(TenantDB.slug == tenant_data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tenant slug already exists")

    tenant = TenantDB(
        id=uuid4(),
        name=tenant_data.name,
        slug=tenant_data.slug,
        plan=TenantPlanDB(tenant_data.plan.value),
        status=TenantStatusDB.TRIAL,
        billing_email=tenant_data.billing_email,
        billing_cycle=BillingCycleDB(tenant_data.billing_cycle.value),
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
        custom_limits=json.dumps(tenant_data.custom_limits) if tenant_data.custom_limits else None,
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    logger.info(f"Created tenant: {tenant.name} ({tenant.slug})")

    return {
        "success": True,
        "message": "Tenant created successfully",
        "data": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        },
    }


@router.get("/{tenant_id}", response_model=dict)
async def get_tenant(
    tenant_id: str,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "success": True,
        "message": "Tenant retrieved",
        "data": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "billing_email": tenant.billing_email,
            "billing_cycle": tenant.billing_cycle.value,
            "custom_domain": tenant.custom_domain,
            "is_active": tenant.status == TenantStatusDB.ACTIVE,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "subscription_ends_at": tenant.subscription_ends_at.isoformat()
            if tenant.subscription_ends_at
            else None,
            "created_at": tenant.created_at.isoformat(),
        },
    }


@router.patch("/{tenant_id}", response_model=dict)
async def update_tenant(
    tenant_id: str,
    request: Request,
    update_data: TenantUpdate,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_fields = update_data.dict(exclude_unset=True)

    if "branding" in update_fields:
        update_fields["branding_settings"] = json.dumps(update_fields.pop("branding"))
    if "settings" in update_fields:
        update_fields["settings"] = json.dumps(update_fields.pop("settings"))

    for key, value in update_fields.items():
        if hasattr(tenant, key):
            setattr(tenant, key, value)

    tenant.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(tenant)

    logger.info(f"Updated tenant {tenant_id}: {list(update_fields.keys())}")

    return {
        "success": True,
        "message": "Tenant updated",
        "data": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value,
        },
    }


@router.post("/{tenant_id}/upgrade", response_model=dict)
async def upgrade_plan(
    tenant_id: str,
    request: Request,
    upgrade_data: PlanUpgrade,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_plan = tenant.plan
    new_plan = TenantPlanDB(upgrade_data.plan.value)
    new_cycle = BillingCycleDB(upgrade_data.billing_cycle.value)

    tenant.plan = new_plan
    tenant.billing_cycle = new_cycle
    tenant.status = TenantStatusDB.ACTIVE
    tenant.subscription_ends_at = datetime.now(timezone.utc) + timedelta(
        days=365 if new_cycle == BillingCycleDB.YEARLY else 30
    )
    tenant.updated_at = datetime.now(timezone.utc)

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="plan_upgrade",
        amount=PLAN_PRICING.get(upgrade_data.plan, {}).get(upgrade_data.billing_cycle.value, 0)
        * 100,
        currency="usd",
        status="pending",
        extra_data=json.dumps(
            {
                "old_plan": old_plan.value,
                "new_plan": new_plan.value,
                "billing_cycle": new_cycle.value,
            }
        ),
    )
    session.add(billing_event)

    await session.commit()
    await session.refresh(tenant)

    logger.info(f"Tenant {tenant_id} upgraded from {old_plan.value} to {new_plan.value}")

    return {
        "success": True,
        "message": "Plan upgraded successfully",
        "data": {
            "id": str(tenant.id),
            "old_plan": old_plan.value,
            "new_plan": tenant.plan.value,
            "billing_cycle": tenant.billing_cycle.value,
            "subscription_ends_at": tenant.subscription_ends_at.isoformat(),
        },
    }


@router.post("/{tenant_id}/suspend", response_model=dict)
async def suspend_tenant(
    tenant_id: str,
    request: Request,
    reason: str = Query("", max_length=500),
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = TenantStatusDB.SUSPENDED
    tenant.updated_at = datetime.now(timezone.utc)

    billing_event = BillingEventDB(
        id=uuid4(),
        tenant_id=tenant.id,
        event_type="tenant_suspended",
        status="completed",
        extra_data=json.dumps({"reason": reason}),
    )
    session.add(billing_event)

    await session.commit()

    logger.warning(f"Tenant {tenant_id} suspended: {reason}")

    return {
        "success": True,
        "message": "Tenant suspended",
        "data": {"id": str(tenant.id), "status": tenant.status.value},
    }


@router.post("/{tenant_id}/reactivate", response_model=dict)
async def reactivate_tenant(
    tenant_id: str,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = TenantStatusDB.ACTIVE
    tenant.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.info(f"Tenant {tenant_id} reactivated")

    return {
        "success": True,
        "message": "Tenant reactivated",
        "data": {"id": str(tenant.id), "status": tenant.status.value},
    }


@router.get("/{tenant_id}/usage", response_model=dict)
async def get_usage(
    tenant_id: str,
    request: Request,
    resource_type: Optional[str] = None,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query = select(UsageRecordDB).where(
        and_(
            UsageRecordDB.tenant_id == tenant.id,
            UsageRecordDB.timestamp >= start_of_month,
        )
    )

    if resource_type:
        query = query.where(UsageRecordDB.resource_type == resource_type)

    result = await session.execute(query)
    records = result.scalars().all()

    usage_summary: Dict[str, int] = {}
    for record in records:
        if record.resource_type not in usage_summary:
            usage_summary[record.resource_type] = 0
        usage_summary[record.resource_type] += record.quantity

    plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan.value), PLAN_LIMITS[TenantPlan.FREE])

    quota_map = {
        "consent": "max_consents_per_month",
        "api_call": "max_api_calls_per_month",
        "fiduciary": "max_fiduciaries",
        "webhook": "max_webhooks",
        "team_member": "max_team_members",
    }

    quotas = []
    for res_type, limit_key in quota_map.items():
        limit = plan_limits.get(limit_key, 0)
        current = usage_summary.get(res_type, 0)
        unlimited = limit == -1

        quotas.append(
            {
                "resource_type": res_type,
                "limit": limit,
                "current": current,
                "remaining": max(0, limit - current) if not unlimited else -1,
                "unlimited": unlimited,
                "allowed": unlimited or current < limit,
            }
        )

    return {
        "success": True,
        "message": "Usage retrieved",
        "data": {
            "tenant_id": str(tenant.id),
            "plan": tenant.plan.value,
            "period_start": start_of_month.isoformat(),
            "period_end": now.isoformat(),
            "usage": usage_summary,
            "quotas": quotas,
        },
    }


@router.post("/{tenant_id}/usage", response_model=dict)
async def record_usage(
    tenant_id: str,
    usage_data: UsageRecordCreate,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    record = UsageRecordDB(
        id=uuid4(),
        tenant_id=tenant.id,
        resource_type=usage_data.resource_type,
        quantity=usage_data.quantity,
        extra_data=json.dumps(usage_data.metadata) if usage_data.metadata else None,
    )

    session.add(record)
    await session.commit()

    return {
        "success": True,
        "message": "Usage recorded",
        "data": {
            "record_id": str(record.id),
            "resource_type": record.resource_type,
            "quantity": record.quantity,
        },
    }


@router.get("/{tenant_id}/quota/{resource_type}", response_model=dict)
async def check_quota(
    tenant_id: str,
    resource_type: str,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan.value), PLAN_LIMITS[TenantPlan.FREE])

    quota_map = {
        "consent": "max_consents_per_month",
        "api_call": "max_api_calls_per_month",
        "fiduciary": "max_fiduciaries",
        "webhook": "max_webhooks",
        "team_member": "max_team_members",
    }

    limit_key = quota_map.get(resource_type)
    if not limit_key:
        return {
            "success": True,
            "message": "Unknown resource type",
            "data": {"allowed": True, "reason": "Unknown resource type"},
        }

    limit = plan_limits.get(limit_key, 0)

    if limit == -1:
        return {
            "success": True,
            "message": "Quota check passed",
            "data": {
                "allowed": True,
                "limit": -1,
                "current": 0,
                "unlimited": True,
            },
        }

    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await session.execute(
        select(func.sum(UsageRecordDB.quantity)).where(
            and_(
                UsageRecordDB.tenant_id == tenant.id,
                UsageRecordDB.resource_type == resource_type,
                UsageRecordDB.timestamp >= start_of_month,
            )
        )
    )
    current = result.scalar() or 0

    return {
        "success": True,
        "message": "Quota check completed",
        "data": {
            "allowed": current < limit,
            "limit": limit,
            "current": current,
            "remaining": max(0, limit - current),
            "unlimited": False,
        },
    }


@router.get("/{tenant_id}/members", response_model=dict)
async def list_members(
    tenant_id: str,
    request: Request,
    role: Optional[str] = None,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = select(TenantMemberDB).where(TenantMemberDB.tenant_id == tenant.id)

    if role:
        query = query.where(TenantMemberDB.role == role)

    result = await session.execute(query)
    members = result.scalars().all()

    return {
        "success": True,
        "message": f"Found {len(members)} members",
        "data": {
            "members": [
                {
                    "id": str(m.id),
                    "user_id": str(m.user_id),
                    "role": m.role,
                    "is_active": m.is_active,
                    "joined_at": m.joined_at.isoformat(),
                }
                for m in members
            ],
        },
    }


@router.post("/{tenant_id}/members", response_model=dict)
async def invite_member(
    tenant_id: str,
    member_data: MemberInvite,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = await session.execute(
        select(TenantMemberDB).where(
            and_(
                TenantMemberDB.tenant_id == tenant.id,
                TenantMemberDB.user_id == member_data.user_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already a member")

    plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan.value), PLAN_LIMITS[TenantPlan.FREE])
    max_members = plan_limits.get("max_team_members", 1)

    if max_members != -1:
        count_result = await session.execute(
            select(func.count()).where(TenantMemberDB.tenant_id == tenant.id)
        )
        current_count = count_result.scalar() or 0

        if current_count >= max_members:
            raise HTTPException(status_code=403, detail="Team member limit reached")

    member = TenantMemberDB(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=member_data.user_id,
        role=member_data.role,
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc),
    )

    session.add(member)
    await session.commit()
    await session.refresh(member)

    return {
        "success": True,
        "message": "Member invited",
        "data": {
            "id": str(member.id),
            "user_id": str(member.user_id),
            "role": member.role,
        },
    }


@router.patch("/{tenant_id}/members/{member_id}", response_model=dict)
async def update_member(
    tenant_id: str,
    member_id: str,
    update_data: MemberUpdate,
    request: Request,
):
    session = request.state.session

    result = await session.execute(
        select(TenantMemberDB).where(
            and_(
                TenantMemberDB.id == UUID(member_id),
                TenantMemberDB.tenant_id == UUID(tenant_id),
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    update_fields = update_data.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if hasattr(member, key):
            setattr(member, key, value)

    await session.commit()
    await session.refresh(member)

    return {
        "success": True,
        "message": "Member updated",
        "data": {
            "id": str(member.id),
            "role": member.role,
            "is_active": member.is_active,
        },
    }


@router.delete("/{tenant_id}/members/{member_id}", response_model=dict)
async def remove_member(
    tenant_id: str,
    member_id: str,
    request: Request,
):
    session = request.state.session

    result = await session.execute(
        select(TenantMemberDB).where(
            and_(
                TenantMemberDB.id == UUID(member_id),
                TenantMemberDB.tenant_id == UUID(tenant_id),
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.soft_delete()
    await session.commit()

    return {
        "success": True,
        "message": "Member removed",
        "data": {"id": str(member.id)},
    }


@router.get("/{tenant_id}/stats", response_model=dict)
async def get_tenant_stats(
    tenant_id: str,
    request: Request,
):
    session = request.state.session

    result = await session.execute(select(TenantDB).where(TenantDB.id == UUID(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan.value), PLAN_LIMITS[TenantPlan.FREE])

    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usage_result = await session.execute(
        select(UsageRecordDB).where(
            and_(
                UsageRecordDB.tenant_id == tenant.id,
                UsageRecordDB.timestamp >= start_of_month,
            )
        )
    )
    usage_records = usage_result.scalars().all()

    usage_summary: Dict[str, int] = {}
    for record in usage_records:
        if record.resource_type not in usage_summary:
            usage_summary[record.resource_type] = 0
        usage_summary[record.resource_type] += record.quantity

    members_count = await session.scalar(
        select(func.count()).where(TenantMemberDB.tenant_id == tenant.id)
    )

    return {
        "success": True,
        "message": "Tenant stats retrieved",
        "data": {
            "tenant_id": str(tenant.id),
            "name": tenant.name,
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "billing_cycle": tenant.billing_cycle.value,
            "usage": usage_summary,
            "limits": {
                "consents": plan_limits.get("max_consents_per_month", 0),
                "api_calls": plan_limits.get("max_api_calls_per_month", 0),
                "fiduciaries": plan_limits.get("max_fiduciaries", 0),
                "webhooks": plan_limits.get("max_webhooks", 0),
                "team_members": plan_limits.get("max_team_members", 0),
            },
            "features": plan_limits.get("features", []),
            "members_count": members_count or 0,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "subscription_ends_at": tenant.subscription_ends_at.isoformat()
            if tenant.subscription_ends_at
            else None,
        },
    }


@router.get("/plans", response_model=dict)
async def list_plans():
    plans = []
    for plan in TenantPlan:
        limits = PLAN_LIMITS.get(plan, {})
        pricing = PLAN_PRICING.get(plan, {})

        plans.append(
            {
                "name": plan.value,
                "limits": {
                    "max_fiduciaries": limits.get("max_fiduciaries", 0),
                    "max_consents_per_month": limits.get("max_consents_per_month", 0),
                    "max_api_calls_per_month": limits.get("max_api_calls_per_month", 0),
                    "max_webhooks": limits.get("max_webhooks", 0),
                    "max_team_members": limits.get("max_team_members", 0),
                    "retention_days": limits.get("retention_days", 30),
                },
                "features": limits.get("features", []),
                "pricing": {
                    "monthly": pricing.get("monthly", 0),
                    "yearly": pricing.get("yearly", 0),
                },
            }
        )

    return {
        "success": True,
        "message": "Plans retrieved",
        "data": {"plans": plans},
    }
