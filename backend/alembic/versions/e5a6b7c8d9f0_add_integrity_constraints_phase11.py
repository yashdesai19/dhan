"""add_integrity_constraints_phase11

Database-level backstops for rules the API already enforces, so a bug, a direct SQL write or a
Django admin edit can't store an impossible value.

Revision ID: e5a6b7c8d9f0
Revises: d4f1b2c7e8a9
Create Date: 2026-10-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5a6b7c8d9f0'
down_revision: Union[str, None] = 'd4f1b2c7e8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHECKS = [
    ('users', 'ck_users_role', "role IN ('user', 'admin')"),
    ('users', 'ck_users_status', "status IN ('active', 'disabled')"),
    ('dhan_transactions', 'ck_dhan_transactions_amount_positive', 'amount > 0'),
    ('dhan_transactions', 'ck_dhan_transactions_type', "transaction_type IN ('expense', 'income', 'transfer')"),
    ('dhan_transactions', 'ck_dhan_transactions_status', "status IN ('completed', 'pending', 'failed', 'cancelled')"),
    ('dhan_goals', 'ck_dhan_goals_target_positive', 'target_amount > 0'),
    ('dhan_goals', 'ck_dhan_goals_saved_not_negative', 'current_amount >= 0'),
    ('dhan_goal_contributions', 'ck_dhan_goal_contributions_amount_positive', 'amount > 0'),
    ('dhan_recurring_payments', 'ck_dhan_recurring_payments_amount_positive', 'amount > 0'),
    ('dhan_budgets', 'ck_dhan_budgets_amount_positive', 'amount > 0'),
    ('dhan_splits', 'ck_dhan_splits_amount_positive', 'amount > 0'),
    ('dhan_settlements', 'ck_dhan_settlements_amount_positive', 'amount > 0'),
]


def upgrade() -> None:
    for table, name, condition in CHECKS:
        op.create_check_constraint(name, table, condition)
    # Emails are looked up case-insensitively, so they must be unique case-insensitively too
    op.execute('CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS uq_users_email_lower')
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table, type_='check')
