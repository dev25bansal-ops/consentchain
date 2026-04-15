"""add blockchain operations tracking table

Revision ID: 006
Revises: 005
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'blockchain_operations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('consent_id', sa.String(36), sa.ForeignKey('consent_records.id')),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('transaction_id', sa.String(100)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Index('idx_blockchain_consent', 'consent_id'),
        sa.Index('idx_blockchain_status', 'status'),
    )


def downgrade():
    op.drop_table('blockchain_operations')
