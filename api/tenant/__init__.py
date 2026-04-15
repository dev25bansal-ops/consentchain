"""Multi-Tenant SaaS Architecture for ConsentChain.

Provides:
- Tenant isolation (database row-level security)
- Tenant management and onboarding
- Usage tracking and quota enforcement
- Plan-based feature access
- Billing integration hooks
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import json
import logging
import os

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

logger = logging.getLogger(__name__)


class TenantPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


PLAN_LIMITS = {
    TenantPlan.FREE: {
        "max_fiduciaries": 1,
        "max_consents_per_month": 100,
        "max_api_calls_per_month": 1000,
        "max_webhooks": 2,
        "max_team_members": 1,
        "retention_days": 30,
        "features": ["basic_consent", "basic_audit"],
    },
    TenantPlan.STARTER: {
        "max_fiduciaries": 3,
        "max_consents_per_month": 1000,
        "max_api_calls_per_month": 10000,
        "max_webhooks": 5,
        "max_team_members": 3,
        "retention_days": 90,
        "features": ["basic_consent", "basic_audit", "webhooks", "export"],
    },
    TenantPlan.PROFESSIONAL: {
        "max_fiduciaries": 10,
        "max_consents_per_month": 10000,
        "max_api_calls_per_month": 100000,
        "max_webhooks": 20,
        "max_team_members": 10,
        "retention_days": 365,
        "features": [
            "basic_consent",
            "basic_audit",
            "webhooks",
            "export",
            "analytics",
            "templates",
            "multi_language",
            "api_access",
        ],
    },
    TenantPlan.ENTERPRISE: {
        "max_fiduciaries": -1,  # Unlimited
        "max_consents_per_month": -1,
        "max_api_calls_per_month": -1,
        "max_webhooks": -1,
        "max_team_members": -1,
        "retention_days": 2555,  # 7 years
        "features": [
            "basic_consent",
            "basic_audit",
            "webhooks",
            "export",
            "analytics",
            "templates",
            "multi_language",
            "api_access",
            "sso",
            "custom_branding",
            "priority_support",
            "dedicated_instance",
            "audit_export",
            "compliance_reports",
            "api_rate_limit_custom",
        ],
    },
    TenantPlan.CUSTOM: {
        "max_fiduciaries": -1,
        "max_consents_per_month": -1,
        "max_api_calls_per_month": -1,
        "max_webhooks": -1,
        "max_team_members": -1,
        "retention_days": 2555,
        "features": ["*"],  # All features
    },
}

PLAN_PRICING = {
    TenantPlan.FREE: {"monthly": 0, "yearly": 0},
    TenantPlan.STARTER: {"monthly": 29, "yearly": 290},
    TenantPlan.PROFESSIONAL: {"monthly": 99, "yearly": 990},
    TenantPlan.ENTERPRISE: {"monthly": 299, "yearly": 2990},
    TenantPlan.CUSTOM: {"monthly": 0, "yearly": 0},  # Custom pricing
}


@dataclass
class Tenant:
    """Tenant entity representing a SaaS customer."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.TRIAL
    billing_email: str = ""
    billing_cycle: BillingCycle = BillingCycle.MONTHLY

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None

    settings: Dict[str, Any] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, int] = field(default_factory=dict)

    custom_domain: Optional[str] = None
    branding: Dict[str, Any] = field(default_factory=dict)

    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    @property
    def is_trial(self) -> bool:
        return self.status == TenantStatus.TRIAL

    @property
    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    @property
    def is_suspended(self) -> bool:
        return self.status == TenantStatus.SUSPENDED

    def get_limit(self, limit_name: str) -> int:
        """Get limit value for this tenant."""
        if limit_name in self.limits:
            return self.limits[limit_name]

        plan_limits = PLAN_LIMITS.get(self.plan, PLAN_LIMITS[TenantPlan.FREE])
        return plan_limits.get(limit_name, 0)

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has access to a feature."""
        plan_limits = PLAN_LIMITS.get(self.plan, PLAN_LIMITS[TenantPlan.FREE])
        features = plan_limits.get("features", [])

        if "*" in features:
            return True

        return feature in features

    def check_quota(self, quota_name: str, current_usage: int) -> bool:
        """Check if usage is within quota."""
        limit = self.get_limit(quota_name)

        if limit == -1:  # Unlimited
            return True

        return current_usage < limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan.value,
            "status": self.status.value,
            "billing_email": self.billing_email,
            "billing_cycle": self.billing_cycle.value,
            "created_at": self.created_at.isoformat(),
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "subscription_ends_at": self.subscription_ends_at.isoformat()
            if self.subscription_ends_at
            else None,
            "custom_domain": self.custom_domain,
            "is_active": self.is_active,
        }


@dataclass
class TenantMember:
    """Member of a tenant."""

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    role: str = "member"  # owner, admin, member, viewer
    invited_by: Optional[UUID] = None
    invited_at: Optional[datetime] = None
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class UsageRecord:
    """Usage record for billing."""

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    resource_type: str = ""  # consent, api_call, webhook, storage
    quantity: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class TenantService:
    """Service for managing tenants."""

    def __init__(self):
        self._tenants: Dict[UUID, Tenant] = {}
        self._slug_index: Dict[str, UUID] = {}
        self._usage: Dict[UUID, List[UsageRecord]] = {}

    def create_tenant(
        self,
        name: str,
        slug: str,
        plan: TenantPlan = TenantPlan.FREE,
        billing_email: str = "",
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        custom_limits: Optional[Dict[str, int]] = None,
    ) -> Tenant:
        """Create a new tenant."""
        if slug in self._slug_index:
            raise ValueError(f"Tenant slug '{slug}' already exists")

        tenant = Tenant(
            id=uuid4(),
            name=name,
            slug=slug,
            plan=plan,
            status=TenantStatus.TRIAL,
            billing_email=billing_email,
            billing_cycle=billing_cycle,
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
        )

        if custom_limits:
            tenant.limits = custom_limits

        self._tenants[tenant.id] = tenant
        self._slug_index[slug] = tenant.id
        self._usage[tenant.id] = []

        logger.info(f"Created tenant: {name} ({slug}) with plan {plan.value}")
        return tenant

    def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        tenant_id = self._slug_index.get(slug)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    def update_tenant(
        self,
        tenant_id: UUID,
        **updates,
    ) -> Optional[Tenant]:
        """Update tenant properties."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.updated_at = datetime.now(timezone.utc)

        logger.info(f"Updated tenant {tenant_id}: {list(updates.keys())}")
        return tenant

    def upgrade_plan(
        self,
        tenant_id: UUID,
        new_plan: TenantPlan,
        billing_cycle: Optional[BillingCycle] = None,
    ) -> Optional[Tenant]:
        """Upgrade tenant plan."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        old_plan = tenant.plan
        tenant.plan = new_plan

        if billing_cycle:
            tenant.billing_cycle = billing_cycle

        tenant.status = TenantStatus.ACTIVE
        tenant.subscription_ends_at = datetime.now(timezone.utc) + timedelta(
            days=365 if billing_cycle == BillingCycle.YEARLY else 30
        )
        tenant.updated_at = datetime.now(timezone.utc)

        logger.info(f"Tenant {tenant_id} upgraded from {old_plan.value} to {new_plan.value}")
        return tenant

    def suspend_tenant(
        self,
        tenant_id: UUID,
        reason: str = "",
    ) -> Optional[Tenant]:
        """Suspend a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.now(timezone.utc)

        logger.warning(f"Tenant {tenant_id} suspended: {reason}")
        return tenant

    def reactivate_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Reactivate a suspended tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.now(timezone.utc)

        logger.info(f"Tenant {tenant_id} reactivated")
        return tenant

    def record_usage(
        self,
        tenant_id: UUID,
        resource_type: str,
        quantity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record resource usage for billing."""
        record = UsageRecord(
            tenant_id=tenant_id,
            resource_type=resource_type,
            quantity=quantity,
            metadata=metadata or {},
        )

        if tenant_id not in self._usage:
            self._usage[tenant_id] = []
        self._usage[tenant_id].append(record)

        return record

    def get_usage(
        self,
        tenant_id: UUID,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Get usage summary for a tenant."""
        records = self._usage.get(tenant_id, [])

        usage_summary: Dict[str, int] = {}

        for record in records:
            if resource_type and record.resource_type != resource_type:
                continue

            if start_date and record.timestamp < start_date:
                continue

            if end_date and record.timestamp > end_date:
                continue

            if record.resource_type not in usage_summary:
                usage_summary[record.resource_type] = 0
            usage_summary[record.resource_type] += record.quantity

        return usage_summary

    def get_monthly_usage(self, tenant_id: UUID) -> Dict[str, int]:
        """Get current month's usage."""
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return self.get_usage(tenant_id, start_date=start_of_month)

    def check_quota(
        self,
        tenant_id: UUID,
        resource_type: str,
    ) -> Dict[str, Any]:
        """Check if tenant is within quota."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {"allowed": False, "reason": "Tenant not found"}

        quota_map = {
            "consent": "max_consents_per_month",
            "api_call": "max_api_calls_per_month",
            "fiduciary": "max_fiduciaries",
            "webhook": "max_webhooks",
            "team_member": "max_team_members",
        }

        limit_key = quota_map.get(resource_type)
        if not limit_key:
            return {"allowed": True, "reason": "Unknown resource type"}

        limit = tenant.get_limit(limit_key)

        if limit == -1:
            return {"allowed": True, "limit": -1, "current": 0, "unlimited": True}

        current_usage = self.get_monthly_usage(tenant_id).get(resource_type, 0)

        return {
            "allowed": current_usage < limit,
            "limit": limit,
            "current": current_usage,
            "remaining": max(0, limit - current_usage),
            "unlimited": False,
        }

    def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        plan: Optional[TenantPlan] = None,
        limit: int = 100,
    ) -> List[Tenant]:
        """List tenants with optional filters."""
        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]

        if plan:
            tenants = [t for t in tenants if t.plan == plan]

        return tenants[:limit]

    def get_tenant_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get tenant statistics."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {}

        monthly_usage = self.get_monthly_usage(tenant_id)

        return {
            "tenant_id": str(tenant_id),
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "usage": monthly_usage,
            "limits": {
                "consents": tenant.get_limit("max_consents_per_month"),
                "api_calls": tenant.get_limit("max_api_calls_per_month"),
                "fiduciaries": tenant.get_limit("max_fiduciaries"),
                "webhooks": tenant.get_limit("max_webhooks"),
                "team_members": tenant.get_limit("max_team_members"),
            },
            "features": PLAN_LIMITS.get(tenant.plan, {}).get("features", []),
        }


tenant_service = TenantService()


class TenantCreate(BaseModel):
    """Request to create a tenant."""

    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern="^[a-z0-9-]+$")
    plan: TenantPlan = TenantPlan.FREE
    billing_email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    custom_limits: Optional[Dict[str, int]] = None


class TenantUpdate(BaseModel):
    """Request to update a tenant."""

    name: Optional[str] = None
    billing_email: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    custom_domain: Optional[str] = None
    branding: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class PlanUpgrade(BaseModel):
    """Request to upgrade plan."""

    plan: TenantPlan
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class TenantResponse(BaseModel):
    """Tenant response."""

    id: str
    name: str
    slug: str
    plan: str
    status: str
    billing_email: str
    billing_cycle: str
    custom_domain: Optional[str]
    is_active: bool
    trial_ends_at: Optional[str]
    subscription_ends_at: Optional[str]
    created_at: str


class UsageResponse(BaseModel):
    """Usage response."""

    resource_type: str
    limit: int
    current: int
    remaining: int
    unlimited: bool
    allowed: bool


def get_current_tenant(tenant_id: Optional[UUID] = None) -> Optional[Tenant]:
    """Get current tenant from context."""
    if tenant_id:
        return tenant_service.get_tenant(tenant_id)
    return None


def require_tenant() -> Tenant:
    """Require a tenant in context."""
    tenant = get_current_tenant()
    if not tenant:
        raise ValueError("Tenant required")
    return tenant


def require_feature(feature: str):
    """Decorator to require a feature."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            tenant = require_tenant()
            if not tenant.has_feature(feature):
                raise ValueError(f"Feature '{feature}' not available on {tenant.plan.value} plan")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_quota(resource_type: str):
    """Decorator to check quota before operation."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            tenant = require_tenant()
            quota = tenant_service.check_quota(tenant.id, resource_type)
            if not quota["allowed"]:
                raise ValueError(f"Quota exceeded for {resource_type}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
