"""add_include_in_total_phase9

Revision ID: c3e9a5d18f42
Revises: b7d41c9e2a10
Create Date: 2026-10-02 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e9a5d18f42'
down_revision: Union[str, None] = 'b7d41c9e2a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'dhan_accounts',
        sa.Column('include_in_total', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('dhan_accounts', 'include_in_total')
