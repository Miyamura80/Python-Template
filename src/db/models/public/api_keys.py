from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID

from src.db.models import Base


class APIKey(Base):
    """
    API keys for authenticating requests without WorkOS JWT.
    Keys are stored as SHA-256 hashes; only the hash is persisted.
    """

    __tablename__ = "api_keys"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["public.profiles.user_id"],
            name="api_key_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        Index("idx_api_keys_user_id", "user_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    key_prefix = Column(String, nullable=False)
    name = Column(String, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
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
