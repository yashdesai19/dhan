"""add_books

Additive only: an account with no book_id stays in the user's Personal book, so existing
rows and already-installed app versions are unaffected.

Revision ID: c9e0f1a2b3d4
Revises: b8d9e0f1a2c3
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e0f1a2b3d4'
down_revision: Union[str, None] = 'b8d9e0f1a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dhan_books',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_books_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_books'),
    )
    op.create_index('ix_dhan_books_user_id', 'dhan_books', ['user_id'])
    op.add_column('dhan_accounts', sa.Column('book_id', sa.UUID(), nullable=True))
    op.create_index('ix_dhan_accounts_book_id', 'dhan_accounts', ['book_id'])
    op.create_foreign_key(
        'fk_dhan_accounts_book_id', 'dhan_accounts', 'dhan_books', ['book_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_dhan_accounts_book_id', 'dhan_accounts', type_='foreignkey')
    op.drop_index('ix_dhan_accounts_book_id', table_name='dhan_accounts')
    op.drop_column('dhan_accounts', 'book_id')
    op.drop_index('ix_dhan_books_user_id', table_name='dhan_books')
    op.drop_table('dhan_books')
