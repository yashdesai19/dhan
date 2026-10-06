"""add_ai_conversations_phase10

Revision ID: d4f1b2c7e8a9
Revises: c3e9a5d18f42
Create Date: 2026-10-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4f1b2c7e8a9'
down_revision: Union[str, None] = 'c3e9a5d18f42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dhan_ai_conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=120), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_ai_conversations_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_ai_conversations'),
    )
    op.create_index('ix_dhan_ai_conversations_user_id', 'dhan_ai_conversations', ['user_id'])

    op.create_table(
        'dhan_ai_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(length=40), nullable=True),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('provider', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['dhan_ai_conversations.id'], name='fk_dhan_ai_messages_conversation_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_dhan_ai_messages_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_dhan_ai_messages'),
        sa.UniqueConstraint('conversation_id', 'seq', name='uq_dhan_ai_messages_conversation_seq'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='ck_dhan_ai_messages_role'),
    )
    op.create_index('ix_dhan_ai_messages_user_id', 'dhan_ai_messages', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_dhan_ai_messages_user_id', table_name='dhan_ai_messages')
    op.drop_table('dhan_ai_messages')
    op.drop_index('ix_dhan_ai_conversations_user_id', table_name='dhan_ai_conversations')
    op.drop_table('dhan_ai_conversations')
