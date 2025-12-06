"""add agent conversations history

Revision ID: 8b9c2e1f4c1c
Revises: 062573113f68
Create Date: 2025-12-06 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b9c2e1f4c1c"
down_revision: Union[str, Sequence[str], None] = "062573113f68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.profiles.user_id"],
            name="agent_conversations_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "idx_agent_conversations_user_id",
        "agent_conversations",
        ["user_id"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["public.agent_conversations.id"],
            name="agent_messages_conversation_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "idx_agent_messages_conversation_id",
        "agent_messages",
        ["conversation_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "idx_agent_messages_created_at",
        "agent_messages",
        ["created_at"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "idx_agent_messages_created_at",
        table_name="agent_messages",
        schema="public",
    )
    op.drop_index(
        "idx_agent_messages_conversation_id",
        table_name="agent_messages",
        schema="public",
    )
    op.drop_table("agent_messages", schema="public")

    op.drop_index(
        "idx_agent_conversations_user_id",
        table_name="agent_conversations",
        schema="public",
    )
    op.drop_table("agent_conversations", schema="public")
