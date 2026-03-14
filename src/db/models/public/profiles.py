from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Enum,
    Integer,
    ForeignKeyConstraint,
    Index,
    ForeignKey,
    UUID,
)
from src.db.models import Base
import uuid
import enum
import secrets
import string
from datetime import datetime, timezone


def generate_referral_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class WaitlistStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Profiles(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"],
            ["public.organizations.id"],
            name="profiles_organization_id_fkey",
            ondelete="SET NULL",
            use_alter=True,  # Defer foreign key creation to break circular dependency
        ),
        Index("idx_profiles_organization_id", "organization_id"),
        {"schema": "public"},
    )

    # Row-Level Security (RLS) policies
    # Temporarily removed for WorkOS migration - will add custom auth schema later
    # __rls_policies__ = {
    #     "user_owns_profile": {
    #         "command": "ALL",
    #         "using": "user_id = auth.uid()",
    #         "check": "user_id = auth.uid()",
    #     }
    # }

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    avatar_url = Column(String, nullable=True)

    # Credits system
    credits = Column(Integer, nullable=False, default=0)

    # Referral system
    referral_code = Column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )
    referrer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.user_id"),
        nullable=True,
    )
    referral_count = Column(Integer, nullable=False, default=0)

    # New fields for waitlist system
    is_approved = Column(Boolean, nullable=False, default=False)
    waitlist_status = Column(
        Enum(WaitlistStatus), nullable=False, default=WaitlistStatus.PENDING
    )
    waitlist_signup_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    cohort_id = Column(UUID(as_uuid=True), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)

    # Timezone for streak calculations
    timezone = Column(String, nullable=True, default="UTC")

    # Timestamps - standardized with lambda approach
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
