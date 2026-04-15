"""Tests for Multi-Tenant SaaS functionality."""

import pytest
import os
import sys
from uuid import uuid4
from datetime import datetime, timedelta
import json

os.environ["TESTING"] = "1"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["MASTER_ADDRESS"] = "TEST_ADDRESS"

from api.tenant import (
    TenantPlan,
    TenantStatus,
    BillingCycle,
    TenantService,
    Tenant,
    TenantMember,
    UsageRecord,
    PLAN_LIMITS,
    PLAN_PRICING,
)
from api.tenant.middleware import (
    TenantContext,
    TenantMiddleware,
    TenantQuotaExceeded,
    FeatureNotAvailable,
)


class TestTenantPlan:
    """Test plan configurations."""

    def test_plan_limits_exist(self):
        """All plans have limits configured."""
        for plan in TenantPlan:
            assert plan in PLAN_LIMITS
            limits = PLAN_LIMITS[plan]
            assert "max_fiduciaries" in limits
            assert "max_consents_per_month" in limits
            assert "max_api_calls_per_month" in limits
            assert "features" in limits

    def test_plan_pricing_exist(self):
        """All plans have pricing configured."""
        for plan in TenantPlan:
            assert plan in PLAN_PRICING
            pricing = PLAN_PRICING[plan]
            assert "monthly" in pricing
            assert "yearly" in pricing

    def test_free_plan_limits(self):
        """Free plan has correct limits."""
        limits = PLAN_LIMITS[TenantPlan.FREE]
        assert limits["max_fiduciaries"] == 1
        assert limits["max_consents_per_month"] == 100
        assert limits["max_api_calls_per_month"] == 1000
        assert limits["retention_days"] == 30

    def test_enterprise_plan_unlimited(self):
        """Enterprise plan has unlimited limits."""
        limits = PLAN_LIMITS[TenantPlan.ENTERPRISE]
        assert limits["max_fiduciaries"] == -1
        assert limits["max_consents_per_month"] == -1
        assert limits["max_api_calls_per_month"] == -1

    def test_free_plan_pricing(self):
        """Free plan is free."""
        pricing = PLAN_PRICING[TenantPlan.FREE]
        assert pricing["monthly"] == 0
        assert pricing["yearly"] == 0

    def test_professional_plan_pricing(self):
        """Professional plan has correct pricing."""
        pricing = PLAN_PRICING[TenantPlan.PROFESSIONAL]
        assert pricing["monthly"] == 99
        assert pricing["yearly"] == 990


class TestTenantEntity:
    """Test Tenant entity."""

    def test_tenant_creation(self):
        """Tenant can be created with defaults."""
        tenant = Tenant(name="Test Company", slug="test-company")
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.plan == TenantPlan.FREE
        assert tenant.status == TenantStatus.TRIAL

    def test_tenant_is_trial(self):
        """Tenant is_trial property works."""
        tenant = Tenant(status=TenantStatus.TRIAL)
        assert tenant.is_trial is True

        tenant.status = TenantStatus.ACTIVE
        assert tenant.is_trial is False

    def test_tenant_is_active(self):
        """Tenant is_active property works."""
        tenant = Tenant(status=TenantStatus.ACTIVE)
        assert tenant.is_active is True

        tenant.status = TenantStatus.SUSPENDED
        assert tenant.is_active is False

    def test_tenant_get_limit(self):
        """Tenant get_limit returns correct values."""
        tenant = Tenant(plan=TenantPlan.STARTER)
        limit = tenant.get_limit("max_consents_per_month")
        assert limit == 1000

        tenant.plan = TenantPlan.ENTERPRISE
        limit = tenant.get_limit("max_consents_per_month")
        assert limit == -1

    def test_tenant_has_feature(self):
        """Tenant has_feature checks features correctly."""
        tenant = Tenant(plan=TenantPlan.FREE)
        assert tenant.has_feature("basic_consent") is True
        assert tenant.has_feature("analytics") is False

        tenant.plan = TenantPlan.PROFESSIONAL
        assert tenant.has_feature("analytics") is True

    def test_tenant_check_quota(self):
        """Tenant check_quota works correctly."""
        tenant = Tenant(plan=TenantPlan.STARTER)

        assert tenant.check_quota("max_consents_per_month", 500) is True
        assert tenant.check_quota("max_consents_per_month", 1500) is False

        tenant.plan = TenantPlan.ENTERPRISE
        assert tenant.check_quota("max_consents_per_month", 1000000) is True

    def test_tenant_to_dict(self):
        """Tenant serializes to dict correctly."""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            plan=TenantPlan.PROFESSIONAL,
            status=TenantStatus.ACTIVE,
        )
        data = tenant.to_dict()
        assert data["name"] == "Test"
        assert data["slug"] == "test"
        assert data["plan"] == "professional"
        assert data["status"] == "active"


class TestTenantService:
    """Test TenantService."""

    def setup_method(self):
        """Create fresh service for each test."""
        self.service = TenantService()

    def test_create_tenant(self):
        """Tenant can be created."""
        tenant = self.service.create_tenant(
            name="Test Company",
            slug="test-company",
            plan=TenantPlan.STARTER,
            billing_email="billing@test.com",
        )
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.plan == TenantPlan.STARTER
        assert tenant.status == TenantStatus.TRIAL
        assert tenant.trial_ends_at is not None

    def test_create_tenant_duplicate_slug(self):
        """Duplicate slug raises error."""
        self.service.create_tenant(
            name="Test 1",
            slug="test-slug",
            billing_email="test1@test.com",
        )
        with pytest.raises(ValueError, match="already exists"):
            self.service.create_tenant(
                name="Test 2",
                slug="test-slug",
                billing_email="test2@test.com",
            )

    def test_get_tenant(self):
        """Tenant can be retrieved by ID."""
        created = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        retrieved = self.service.get_tenant(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_tenant_by_slug(self):
        """Tenant can be retrieved by slug."""
        created = self.service.create_tenant(
            name="Test",
            slug="test-slug",
            billing_email="test@test.com",
        )
        retrieved = self.service.get_tenant_by_slug("test-slug")
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_update_tenant(self):
        """Tenant can be updated."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        updated = self.service.update_tenant(tenant.id, name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"

    def test_upgrade_plan(self):
        """Tenant plan can be upgraded."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            plan=TenantPlan.FREE,
            billing_email="test@test.com",
        )
        upgraded = self.service.upgrade_plan(
            tenant.id,
            TenantPlan.PROFESSIONAL,
            BillingCycle.MONTHLY,
        )
        assert upgraded.plan == TenantPlan.PROFESSIONAL
        assert upgraded.status == TenantStatus.ACTIVE
        assert upgraded.subscription_ends_at is not None

    def test_suspend_tenant(self):
        """Tenant can be suspended."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        suspended = self.service.suspend_tenant(tenant.id, "Payment failure")
        assert suspended.status == TenantStatus.SUSPENDED

    def test_reactivate_tenant(self):
        """Tenant can be reactivated."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        self.service.suspend_tenant(tenant.id)
        reactivated = self.service.reactivate_tenant(tenant.id)
        assert reactivated.status == TenantStatus.ACTIVE

    def test_record_usage(self):
        """Usage can be recorded."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        record = self.service.record_usage(
            tenant.id,
            "consent",
            quantity=5,
            metadata={"source": "api"},
        )
        assert record.resource_type == "consent"
        assert record.quantity == 5

    def test_get_usage(self):
        """Usage can be queried."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            billing_email="test@test.com",
        )
        self.service.record_usage(tenant.id, "consent", 10)
        self.service.record_usage(tenant.id, "consent", 5)
        self.service.record_usage(tenant.id, "api_call", 100)

        usage = self.service.get_usage(tenant.id)
        assert usage["consent"] == 15
        assert usage["api_call"] == 100

    def test_check_quota(self):
        """Quota check works correctly."""
        tenant = self.service.create_tenant(
            name="Test",
            slug="test",
            plan=TenantPlan.FREE,
            billing_email="test@test.com",
        )

        quota = self.service.check_quota(tenant.id, "consent")
        assert quota["allowed"] is True
        assert quota["limit"] == 100
        assert quota["remaining"] == 100

    def test_list_tenants(self):
        """Tenants can be listed."""
        self.service.create_tenant(
            name="Test 1",
            slug="test-1",
            billing_email="test1@test.com",
        )
        self.service.create_tenant(
            name="Test 2",
            slug="test-2",
            plan=TenantPlan.PROFESSIONAL,
            billing_email="test2@test.com",
        )

        all_tenants = self.service.list_tenants()
        assert len(all_tenants) == 2

        pro_tenants = self.service.list_tenants(plan=TenantPlan.PROFESSIONAL)
        assert len(pro_tenants) == 1


class TestTenantContext:
    """Test TenantContext middleware."""

    def setup_method(self):
        """Clear context before each test."""
        TenantContext.clear()

    def test_set_and_get_tenant(self):
        """Tenant can be set and retrieved from context."""
        tenant = Tenant(name="Test", slug="test")
        TenantContext.set_tenant(tenant)

        assert TenantContext.get_tenant() == tenant
        assert TenantContext.get_tenant_id() == tenant.id

    def test_has_feature(self):
        """Feature check works in context."""
        tenant = Tenant(plan=TenantPlan.PROFESSIONAL)
        TenantContext.set_tenant(tenant)

        assert TenantContext.has_feature("analytics") is True
        assert TenantContext.has_feature("sso") is False

    def test_get_limit(self):
        """Limit retrieval works in context."""
        tenant = Tenant(plan=TenantPlan.STARTER)
        TenantContext.set_tenant(tenant)

        assert TenantContext.get_limit("max_consents_per_month") == 1000

    def test_clear(self):
        """Context can be cleared."""
        tenant = Tenant(name="Test", slug="test")
        TenantContext.set_tenant(tenant)
        TenantContext.clear()

        assert TenantContext.get_tenant() is None
        assert TenantContext.get_tenant_id() is None


class TestTenantExceptions:
    """Test tenant exceptions."""

    def test_quota_exceeded_message(self):
        """QuotaExceeded has correct message."""
        exc = TenantQuotaExceeded("consent", 150, 100)
        assert exc.resource_type == "consent"
        assert exc.current == 150
        assert exc.limit == 100
        assert "Quota exceeded" in str(exc)

    def test_feature_not_available_message(self):
        """FeatureNotAvailable has correct message."""
        exc = FeatureNotAvailable("sso", "starter")
        assert exc.feature == "sso"
        assert exc.plan == "starter"
        assert "not available" in str(exc)


class TestTenantMember:
    """Test TenantMember entity."""

    def test_member_creation(self):
        """Member can be created."""
        member = TenantMember(
            tenant_id=uuid4(),
            user_id=uuid4(),
            role="admin",
        )
        assert member.role == "admin"
        assert member.is_active is True


class TestUsageRecord:
    """Test UsageRecord entity."""

    def test_usage_record_creation(self):
        """UsageRecord can be created."""
        record = UsageRecord(
            tenant_id=uuid4(),
            resource_type="api_call",
            quantity=10,
        )
        assert record.resource_type == "api_call"
        assert record.quantity == 10
