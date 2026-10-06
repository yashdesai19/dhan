"""split_transactions_phase13

A group expense you pay from one of your accounts is recorded as a 'split' transaction: it moves
the account balance but is not spending (spec section 6). It is linked to its group expense.

Revision ID: a7c8d9e0f1b2
Revises: f6b7c8d9e0a1
Create Date: 2026-10-04 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c8d9e0f1b2'
down_revision: Union[str, None] = 'f6b7c8d9e0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dhan_transactions', sa.Column('split_expense_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_dhan_transactions_split_expense_id', 'dhan_transactions', 'dhan_splits',
        ['split_expense_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_dhan_transactions_split_expense_id', 'dhan_transactions', ['split_expense_id'])
    op.drop_constraint('ck_dhan_transactions_type', 'dhan_transactions', type_='check')
    op.create_check_constraint(
        'ck_dhan_transactions_type', 'dhan_transactions',
        "transaction_type IN ('expense', 'income', 'transfer', 'split')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM dhan_transactions WHERE transaction_type = 'split'")
    op.drop_constraint('ck_dhan_transactions_type', 'dhan_transactions', type_='check')
    op.create_check_constraint(
        'ck_dhan_transactions_type', 'dhan_transactions',
        "transaction_type IN ('expense', 'income', 'transfer')",
    )
    op.drop_index('ix_dhan_transactions_split_expense_id', table_name='dhan_transactions')
    op.drop_constraint('fk_dhan_transactions_split_expense_id', 'dhan_transactions', type_='foreignkey')
    op.drop_column('dhan_transactions', 'split_expense_id')
