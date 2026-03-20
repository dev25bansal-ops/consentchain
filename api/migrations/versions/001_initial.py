"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_principals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_address", sa.String(58), unique=True, nullable=False, index=True),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("kyc_verified", sa.Boolean, default=False),
        sa.Column("preferred_language", sa.String(10), default="en"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "data_fiduciaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(100), unique=True, nullable=False),
        sa.Column("wallet_address", sa.String(58), unique=True, nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("data_categories", sa.Text, nullable=False),
        sa.Column("purposes", sa.Text, nullable=False),
        sa.Column("compliance_status", sa.String(50), default="ACTIVE"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "consent_records",
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
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("data_types", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("granted_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("on_chain_tx_id", sa.String(64), nullable=True),
        sa.Column("on_chain_app_id", sa.Integer, nullable=True),
        sa.Column("consent_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index(
        "ix_consent_records_principal_fiduciary",
        "consent_records",
        ["principal_id", "fiduciary_id"],
    )
    op.create_index("ix_consent_records_status", "consent_records", ["status"])

    op.create_table(
        "consent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "consent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consent_records.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(58), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("tx_id", sa.String(64), nullable=True),
        sa.Column("block_number", sa.Integer, nullable=True),
        sa.Column("ipfs_hash", sa.String(100), nullable=True),
        sa.Column("signature", sa.Text, nullable=True),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_consent_events_consent_id", "consent_events", ["consent_id"])
    op.create_index("ix_consent_events_created_at", "consent_events", ["created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "principal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_principals.id"),
            nullable=True,
        ),
        sa.Column(
            "fiduciary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_fiduciaries.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("on_chain_reference", sa.String(100), nullable=True),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_audit_logs_principal", "audit_logs", ["principal_id"])
    op.create_index("ix_audit_logs_fiduciary", "audit_logs", ["fiduciary_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "merkle_roots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("root_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("event_count", sa.Integer, nullable=False),
        sa.Column("first_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("on_chain_tx_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "compliance_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fiduciary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_fiduciaries.id"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime, nullable=False),
        sa.Column("period_end", sa.DateTime, nullable=False),
        sa.Column("total_consents", sa.Integer, default=0),
        sa.Column("active_consents", sa.Integer, default=0),
        sa.Column("revoked_consents", sa.Integer, default=0),
        sa.Column("expired_consents", sa.Integer, default=0),
        sa.Column("sensitive_data_consents", sa.Integer, default=0),
        sa.Column("third_party_sharing_count", sa.Integer, default=0),
        sa.Column("audit_events", sa.Integer, default=0),
        sa.Column("compliance_score", sa.Integer, default=0),
        sa.Column("on_chain_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("compliance_reports")
    op.drop_table("merkle_roots")
    op.drop_table("audit_logs")
    op.drop_table("consent_events")
    op.drop_table("consent_records")
    op.drop_table("data_fiduciaries")
    op.drop_table("data_principals")
