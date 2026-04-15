"""add cross-border transfers and missing indexes

Revision ID: 005
Revises: 004
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create cross-border transfers table for DPDP compliance tracking
    op.create_table(
        'cross_border_transfers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('fiduciary_id', sa.String(36), nullable=False),
        sa.Column('principal_id', sa.String(36), nullable=False),
        sa.Column('countries', sa.JSON, nullable=False),
        sa.Column('transfer_id', sa.String(36), unique=True, nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Index('ix_transfer_fiduciary', 'fiduciary_id'),
        sa.Index('ix_transfer_principal', 'principal_id'),
    )

    # Add missing performance indexes
    # Note: api_key_hash index is now defined in the model (database.py)
    # but we add it here explicitly for existing deployments
    op.create_index('ix_fiduciary_api_key_hash', 'data_fiduciaries', ['api_key_hash'])
    op.create_index('ix_webhook_sub_fid_active_events', 'webhook_subscriptions', ['fiduciary_id', 'active', 'events'])
    op.create_index('ix_grievance_status_resdate', 'grievances', ['status', 'expected_resolution_date'])
    op.create_index('ix_deletion_status_created', 'deletion_requests', ['status', 'created_at'])
    op.create_index('ix_audit_fiduciary_action', 'audit_logs', ['fiduciary_id', 'action', 'created_at'])


def downgrade():
    op.drop_index('ix_audit_fiduciary_action', 'audit_logs')
    op.drop_index('ix_deletion_status_created', 'deletion_requests')
    op.drop_index('ix_grievance_status_resdate', 'grievances')
    op.drop_index('ix_webhook_sub_fid_active_events', 'webhook_subscriptions')
    op.drop_index('ix_fiduciary_api_key_hash', 'data_fiduciaries')
    op.drop_table('cross_border_transfers')
