"""add mobile devices table

Revision ID: 009
Revises: 008
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'mobile_devices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('principal_id', sa.String(36), sa.ForeignKey('data_principals.id'), nullable=False),
        sa.Column('device_token', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('device_name', sa.String(100)),
        sa.Column('app_version', sa.String(20)),
        sa.Column('os_version', sa.String(20)),
        sa.Column('push_enabled', sa.Boolean, server_default='true'),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Index('ix_mobile_device_principal', 'principal_id'),
        sa.Index('ix_mobile_device_token', 'device_token'),
    )


def downgrade():
    op.drop_table('mobile_devices')
