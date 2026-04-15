"""Add tenant tables and tenant_id to fiduciaries

Revision ID: 004
Revises: 003_deletion_templates_notifications
Create Date: 2026-04-02

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), default="free"),
        sa.Column("status", sa.String(20), default="trial"),
        sa.Column("billing_email", sa.String(255), nullable=False),
        sa.Column("billing_cycle", sa.String(20), default="monthly"),
        sa.Column("custom_domain", sa.String(255), unique=True, nullable=True),
        sa.Column("branding_settings", sa.Text, nullable=True),
        sa.Column("settings", sa.Text, nullable=True),
        sa.Column("custom_limits", sa.Text, nullable=True),
        sa.Column("stripe_customer_id", sa.String(100), unique=True, nullable=True),
        sa.Column("stripe_subscription_id", sa.String(100), unique=True, nullable=True),
        sa.Column("trial_ends_at", sa.DateTime, nullable=True),
        sa.Column("subscription_ends_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_plan", "tenants", ["plan"])
    op.create_index("ix_tenants_status", "tenants", ["status"])

    op.create_table(
        "tenant_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), default="member"),
        sa.Column("invited_by", UUID(as_uuid=True), nullable=True),
        sa.Column("invited_at", sa.DateTime, nullable=True),
        sa.Column("joined_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_tenant_members_tenant_id", "tenant_members", ["tenant_id"])
    op.create_index("ix_tenant_members_user_id", "tenant_members", ["user_id"])
    op.create_index("ix_tenant_members_role", "tenant_members", ["role"])

    op.create_table(
        "usage_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer, default=1),
        sa.Column("extra_data", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_usage_records_tenant_id", "usage_records", ["tenant_id"])
    op.create_index("ix_usage_records_resource_type", "usage_records", ["resource_type"])
    op.create_index("ix_usage_records_timestamp", "usage_records", ["timestamp"])

    op.create_table(
        "billing_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("stripe_event_id", sa.String(100), unique=True, nullable=True),
        sa.Column("amount", sa.Integer, nullable=True),
        sa.Column("currency", sa.String(3), default="usd"),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("extra_data", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_billing_events_tenant_id", "billing_events", ["tenant_id"])
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])

    op.add_column(
        "data_fiduciaries",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
    )
    op.create_index("ix_data_fiduciaries_tenant_id", "data_fiduciaries", ["tenant_id"])


def downgrade():
    op.drop_index("ix_data_fiduciaries_tenant_id", "data_fiduciaries")
    op.drop_column("data_fiduciaries", "tenant_id")

    op.drop_table("billing_events")
    op.drop_table("usage_records")
    op.drop_table("tenant_members")
    op.drop_table("tenants")
