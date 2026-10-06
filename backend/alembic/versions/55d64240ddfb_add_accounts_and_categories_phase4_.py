"""add_accounts_and_categories_phase4_fields

Revision ID: 55d64240ddfb
Revises: fc8a7b33736a
Create Date: 2026-10-02 16:39:37.365012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55d64240ddfb'
down_revision: Union[str, None] = 'fc8a7b33736a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # dhan_accounts columns
    op.add_column('dhan_accounts', sa.Column('archived', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('dhan_accounts', sa.Column('credit_limit', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('dhan_accounts', sa.Column('due_date', sa.Integer(), nullable=True))

    # dhan_categories columns
    op.add_column('dhan_categories', sa.Column('user_id', sa.UUID(), nullable=True))
    op.add_column('dhan_categories', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('dhan_categories', sa.Column('ordering', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('dhan_categories', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.create_index(op.f('ix_dhan_categories_user_id'), 'dhan_categories', ['user_id'], unique=False)
    op.create_foreign_key('fk_dhan_categories_user_id', 'dhan_categories', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_dhan_categories_user_id', 'dhan_categories', type_='foreignkey')
    op.drop_index(op.f('ix_dhan_categories_user_id'), table_name='dhan_categories')
    op.drop_column('dhan_categories', 'updated_at')
    op.drop_column('dhan_categories', 'ordering')
    op.drop_column('dhan_categories', 'is_active')
    op.drop_column('dhan_categories', 'user_id')
    op.drop_column('dhan_accounts', 'due_date')
    op.drop_column('dhan_accounts', 'credit_limit')
    op.drop_column('dhan_accounts', 'archived')
