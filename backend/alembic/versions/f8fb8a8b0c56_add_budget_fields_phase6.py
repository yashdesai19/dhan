"""add_budget_fields_phase6

Revision ID: f8fb8a8b0c56
Revises: ea02c7effc30
Create Date: 2026-10-02 17:40:31.029390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8fb8a8b0c56'
down_revision: Union[str, None] = 'ea02c7effc30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Allow category_id to be nullable for overall monthly budgets
    op.alter_column('dhan_budgets', 'category_id', existing_type=sa.UUID(), nullable=True)

    # Add month column (e.g. '2026-09')
    op.add_column('dhan_budgets', sa.Column('month', sa.String(length=7), nullable=True))
    op.execute("UPDATE dhan_budgets SET month = to_char(start_date, 'YYYY-MM') WHERE month IS NULL")

    # Add warn_at_percent and rollover
    op.add_column('dhan_budgets', sa.Column('warn_at_percent', sa.Integer(), server_default='90', nullable=False))
    op.add_column('dhan_budgets', sa.Column('rollover', sa.Boolean(), server_default='false', nullable=False))

    # Add index on user_id and month for rapid budget filtering
    op.create_index('ix_dhan_budgets_user_month', 'dhan_budgets', ['user_id', 'month'])


def downgrade() -> None:
    op.drop_index('ix_dhan_budgets_user_month', table_name='dhan_budgets')
    op.drop_column('dhan_budgets', 'rollover')
    op.drop_column('dhan_budgets', 'warn_at_percent')
    op.drop_column('dhan_budgets', 'month')
    op.alter_column('dhan_budgets', 'category_id', existing_type=sa.UUID(), nullable=False)
