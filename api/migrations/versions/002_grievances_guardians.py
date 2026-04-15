"""Add grievances and guardians tables for DPDP compliance

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grievances",
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
        sa.Column("grievance_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, default="SUBMITTED"),
        sa.Column("priority", sa.String(20), nullable=False, default="MEDIUM"),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_data", sa.Text, nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolution_date", sa.DateTime, nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledgement_date", sa.DateTime, nullable=True),
        sa.Column("expected_resolution_date", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_grievances_principal_id", "grievances", ["principal_id"])
    op.create_index("ix_grievances_fiduciary_id", "grievances", ["fiduciary_id"])
    op.create_index("ix_grievances_status", "grievances", ["status"])
    op.create_index("ix_grievances_created_at", "grievances", ["created_at"])

    op.create_table(
        "grievance_communications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "grievance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grievances.id"),
            nullable=False,
        ),
        sa.Column("sender_type", sa.String(50), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("attachments", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_grievance_communications_grievance_id", "grievance_communications", ["grievance_id"]
    )

    op.create_table(
        "guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guardian_wallet", sa.String(58), nullable=False),
        sa.Column("guardian_name", sa.String(255), nullable=False),
        sa.Column("guardian_email", sa.String(255), nullable=False),
        sa.Column("guardian_phone", sa.String(20), nullable=True),
        sa.Column("guardian_type", sa.String(50), nullable=False),
        sa.Column(
            "principal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_principals.id"),
            nullable=False,
        ),
        sa.Column("principal_category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, default="PENDING_VERIFICATION"),
        sa.Column("relationship_document", sa.Text, nullable=True),
        sa.Column("verification_document", sa.Text, nullable=True),
        sa.Column("verification_date", sa.DateTime, nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.Text, nullable=False, default="FULL"),
        sa.Column("valid_from", sa.DateTime, nullable=False),
        sa.Column("valid_until", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index("ix_guardians_guardian_wallet", "guardians", ["guardian_wallet"])
    op.create_index("ix_guardians_principal_id", "guardians", ["principal_id"])
    op.create_index("ix_guardians_status", "guardians", ["status"])

    op.create_table(
        "guardian_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "guardian_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("guardians.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("old_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_guardian_audit_guardian_id", "guardian_audit", ["guardian_id"])


def downgrade() -> None:
    op.drop_table("guardian_audit")
    op.drop_table("guardians")
    op.drop_table("grievance_communications")
    op.drop_table("grievances")
