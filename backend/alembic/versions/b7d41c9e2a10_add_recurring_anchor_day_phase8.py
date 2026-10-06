"""add_recurring_anchor_day_phase8

Revision ID: b7d41c9e2a10
Revises: e2084b1239aa
Create Date: 2026-10-02 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d41c9e2a10'
down_revision: Union[str, None] = 'e2084b1239aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dhan_recurring_payments', sa.Column('anchor_day', sa.SmallInteger(), nullable=True))
    op.execute(
        "UPDATE dhan_recurring_payments SET anchor_day = EXTRACT(DAY FROM next_due_date)::smallint"
    )


def downgrade() -> None:
    op.drop_column('dhan_recurring_payments', 'anchor_day')
