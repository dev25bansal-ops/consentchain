"""add token blacklist table

Revision ID: 007
Revises: 006
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('jti', sa.String(36), unique=True, nullable=False),
        sa.Column('token_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('blacklisted_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('reason', sa.String(100)),
        sa.Index('idx_token_expires', 'expires_at'),
    )


def downgrade():
    op.drop_table('token_blacklist')
