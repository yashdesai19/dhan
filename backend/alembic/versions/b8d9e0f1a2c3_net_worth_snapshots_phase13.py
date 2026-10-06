"""net_worth_snapshots_phase13

Revision ID: b8d9e0f1a2c3
Revises: a7c8d9e0f1b2
Create Date: 2026-10-04 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8d9e0f1a2c3'
down_revision: Union[str, None] = 'a7c8d9e0f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dhan_net_worth_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('month', sa.String(length=7), nullable=False),
        sa.Column('net_worth', sa.Numeric(15, 2), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_net_worth_snapshots_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_net_worth_snapshots'),
        sa.UniqueConstraint('user_id', 'month', name='uq_dhan_net_worth_snapshots_user_month'),
    )


def downgrade() -> None:
    op.drop_table('dhan_net_worth_snapshots')
