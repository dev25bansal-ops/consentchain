"""add webauthn credentials table

Revision ID: 008
Revises: 007
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'webauthn_credentials',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('principal_id', sa.String(36), sa.ForeignKey('data_principals.id'), nullable=False),
        sa.Column('credential_id', sa.String(255), unique=True, nullable=False),
        sa.Column('credential_public_key', sa.LargeBinary, nullable=False),
        sa.Column('sign_count', sa.Integer, server_default='0'),
        sa.Column('transport', sa.JSON),
        sa.Column('device_type', sa.String(50), server_default='single_device'),
        sa.Column('backup_eligible', sa.Boolean, server_default='false'),
        sa.Column('backup_state', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Index('ix_webauthn_principal', 'principal_id'),
        sa.Index('ix_webauthn_credential_id', 'credential_id'),
    )


def downgrade():
    op.drop_table('webauthn_credentials')
