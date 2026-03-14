from sqlalchemy import Column, String, DateTime, ForeignKeyConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from src.db.models import Base
import uuid
from datetime import datetime, timezone


class Organizations(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_user_id"],
            ["public.profiles.user_id"],
            name="organizations_owner_user_id_fkey",
            ondelete="SET NULL",  # Or CASCADE depending on desired behavior for owner deletion
            use_alter=True,  # Defer foreign key creation to break circular dependency
        ),
        Index("idx_organizations_owner_user_id", "owner_user_id"),
        {"schema": "public"},  # Assuming public schema, adjust if needed
    )

    # Row-Level Security (RLS) policies
    # Temporarily removed for WorkOS migration - will add custom auth schema later
    # __rls_policies__ = {
    #     "owner_controls_organization": {
    #         "command": "ALL",
    #         "using": "owner_user_id = auth.uid()",
    #         "check": "owner_user_id = auth.uid()",
    #     }
    # }

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    owner_user_id = Column(
        UUID(as_uuid=True), nullable=True
    )  # Can be null if owner profile is deleted
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
