from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Text,
    UUID as SA_UUID,
)
from sqlalchemy.orm import relationship

from src.db.models import Base


class AgentConversation(Base):
    """Conversation container for agent chats."""

    __tablename__ = "agent_conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["public.profiles.user_id"],
            name="agent_conversations_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        Index("idx_agent_conversations_user_id", "user_id"),
        {"schema": "public"},
    )

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SA_UUID(as_uuid=True), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship(
        "AgentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )


class AgentMessage(Base):
    """Individual message within an agent conversation."""

    __tablename__ = "agent_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id"],
            ["public.agent_conversations.id"],
            name="agent_messages_conversation_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        Index("idx_agent_messages_conversation_id", "conversation_id"),
        Index("idx_agent_messages_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(SA_UUID(as_uuid=True), nullable=False)
    role = Column(String, nullable=False)  # e.g., "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship(
        "AgentConversation",
        back_populates="messages",
    )
