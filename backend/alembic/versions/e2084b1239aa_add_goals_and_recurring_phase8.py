"""add_goals_and_recurring_phase8

Revision ID: e2084b1239aa
Revises: 45e4f278ebb0
Create Date: 2026-10-02 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e2084b1239aa'
down_revision: Union[str, None] = '45e4f278ebb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update dhan_goals
    op.add_column('dhan_goals', sa.Column('icon', sa.String(length=50), server_default='target', nullable=False))

    # 2. Create dhan_goal_contributions
    op.create_table(
        'dhan_goal_contributions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('goal_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['dhan_goals.id'], name='fk_dhan_goal_contributions_goal_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_goal_contributions_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['dhan_accounts.id'], name='fk_dhan_goal_contributions_account_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_goal_contributions'),
    )
    op.create_index('ix_dhan_goal_contributions_goal_id', 'dhan_goal_contributions', ['goal_id'])
    op.create_index('ix_dhan_goal_contributions_user_id', 'dhan_goal_contributions', ['user_id'])

    # 3. Update dhan_recurring_payments
    op.add_column('dhan_recurring_payments', sa.Column('kind', sa.String(length=30), server_default='bill', nullable=False))
    op.add_column('dhan_recurring_payments', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('dhan_recurring_payments', sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('dhan_recurring_payments', sa.Column('last_paid_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('dhan_recurring_payments', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    # 3. Revert dhan_recurring_payments
    op.drop_column('dhan_recurring_payments', 'updated_at')
    op.drop_column('dhan_recurring_payments', 'last_paid_at')
    op.drop_column('dhan_recurring_payments', 'metadata_json')
    op.drop_column('dhan_recurring_payments', 'notes')
    op.drop_column('dhan_recurring_payments', 'kind')

    # 2. Drop dhan_goal_contributions
    op.drop_index('ix_dhan_goal_contributions_user_id', table_name='dhan_goal_contributions')
    op.drop_index('ix_dhan_goal_contributions_goal_id', table_name='dhan_goal_contributions')
    op.drop_table('dhan_goal_contributions')

    # 1. Revert dhan_goals
    op.drop_column('dhan_goals', 'icon')
