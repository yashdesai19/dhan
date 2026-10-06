"""add_splits_and_members_phase7

Revision ID: 45e4f278ebb0
Revises: f8fb8a8b0c56
Create Date: 2026-10-02 18:39:09.883168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '45e4f278ebb0'
down_revision: Union[str, None] = 'f8fb8a8b0c56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create dhan_group_members table
    op.create_table(
        'dhan_group_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('group_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['dhan_groups.id'], name='fk_dhan_group_members_group_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_group_members_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_group_members'),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_dhan_group_members_group_user'),
    )
    op.create_index('ix_dhan_group_members_group_id', 'dhan_group_members', ['group_id'])
    op.create_index('ix_dhan_group_members_user_id', 'dhan_group_members', ['user_id'])

    # Backfill group creators into group members
    op.execute(
        "INSERT INTO dhan_group_members (id, group_id, user_id, role, joined_at) "
        "SELECT gen_random_uuid(), id, created_by_id, 'admin', created_at FROM dhan_groups "
        "ON CONFLICT (group_id, user_id) DO NOTHING"
    )

    # 2. Add columns to dhan_splits
    op.add_column('dhan_splits', sa.Column('shares', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column('dhan_splits', sa.Column('split_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('dhan_splits', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('dhan_splits', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # 3. Add columns to dhan_settlements
    op.add_column('dhan_settlements', sa.Column('method', sa.String(length=20), server_default='upi', nullable=False))
    op.add_column('dhan_settlements', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('dhan_settlements', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    # Revert dhan_settlements
    op.drop_column('dhan_settlements', 'updated_at')
    op.drop_column('dhan_settlements', 'notes')
    op.drop_column('dhan_settlements', 'method')

    # Revert dhan_splits
    op.drop_column('dhan_splits', 'updated_at')
    op.drop_column('dhan_splits', 'notes')
    op.drop_column('dhan_splits', 'split_details')
    op.drop_column('dhan_splits', 'shares')

    # Revert dhan_group_members
    op.drop_index('ix_dhan_group_members_user_id', table_name='dhan_group_members')
    op.drop_index('ix_dhan_group_members_group_id', table_name='dhan_group_members')
    op.drop_table('dhan_group_members')
