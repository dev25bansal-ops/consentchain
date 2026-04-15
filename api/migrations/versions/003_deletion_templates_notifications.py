"""Add deletion requests, consent templates, and notifications

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "principal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_principals.id"),
            nullable=False,
        ),
        sa.Column(
            "fiduciary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_fiduciaries.id"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), default="PENDING"),
        sa.Column("consent_ids", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("verification_code", sa.String(64), nullable=False),
        sa.Column("exceptions", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_deletion_principal_status", "deletion_requests", ["principal_id", "status"])
    op.create_index("ix_deletion_fiduciary_status", "deletion_requests", ["fiduciary_id", "status"])

    op.create_table(
        "consent_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, default="en"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("default_data_types", sa.Text, nullable=False),
        sa.Column("default_duration_days", sa.Integer, default=365),
        sa.Column("required_fields", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_consent_templates_name", "consent_templates", ["name"])
    op.create_index("ix_consent_templates_category", "consent_templates", ["category"])
    op.create_index("ix_consent_templates_active", "consent_templates", ["active"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "principal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_principals.id"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("read", sa.Boolean, default=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("extra_data", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("read_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_principal_id", "notifications", ["principal_id"])
    op.create_index("ix_notifications_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_read", "notifications", ["read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notification_principal_read", "notifications", ["principal_id", "read"])

    op.create_index("ix_consent_fiduciary_status", "consent_records", ["fiduciary_id", "status"])
    op.create_index("ix_consent_principal_status", "consent_records", ["principal_id", "status"])
    op.create_index("ix_consent_expires_status", "consent_records", ["expires_at", "status"])
    op.create_index(
        "ix_consent_fiduciary_created", "consent_records", ["fiduciary_id", "created_at"]
    )

    op.create_index("ix_event_consent_created", "consent_events", ["consent_id", "created_at"])
    op.create_index("ix_event_type_created", "consent_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_event_type_created", "consent_events")
    op.drop_index("ix_event_consent_created", "consent_events")
    op.drop_index("ix_consent_fiduciary_created", "consent_records")
    op.drop_index("ix_consent_expires_status", "consent_records")
    op.drop_index("ix_consent_principal_status", "consent_records")
    op.drop_index("ix_consent_fiduciary_status", "consent_records")

    op.drop_index("ix_notification_principal_read", "notifications")
    op.drop_index("ix_notifications_created_at", "notifications")
    op.drop_index("ix_notifications_read", "notifications")
    op.drop_index("ix_notifications_type", "notifications")
    op.drop_index("ix_notifications_principal_id", "notifications")
    op.drop_table("notifications")

    op.drop_index("ix_consent_templates_active", "consent_templates")
    op.drop_index("ix_consent_templates_category", "consent_templates")
    op.drop_index("ix_consent_templates_name", "consent_templates")
    op.drop_table("consent_templates")

    op.drop_index("ix_deletion_fiduciary_status", "deletion_requests")
    op.drop_index("ix_deletion_principal_status", "deletion_requests")
    op.drop_table("deletion_requests")
