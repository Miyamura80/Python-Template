"""
Referrals Model

This model tracks user referrals, including referral codes and their usage.
"""

from datetime import datetime, timezone
import enum
import secrets
import string
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from src.db.models import Base


class ReferralStatus(enum.Enum):
    """Status of a referral."""

    PENDING = "PENDING"  # Code created but not yet used
    COMPLETED = "COMPLETED"  # Referral completed successfully
    EXPIRED = "EXPIRED"  # Referral expired without being used


def generate_referral_code(length: int = 8) -> str:
    """
    Generate a unique referral code.

    Args:
        length: Length of the referral code (default 8)

    Returns:
        A unique alphanumeric referral code
    """
    # Use uppercase letters and digits for readability
    alphabet = string.ascii_uppercase + string.digits
    # Remove potentially confusing characters (0, O, I, 1)
    alphabet = (
        alphabet.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Referral(Base):
    """
    Referral model for tracking user referrals.

    Each user can have one referral code that they share with others.
    When someone signs up using a referral code, both the referrer and
    the referred user can receive credits or other benefits.
    """

    __tablename__ = "referrals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["referrer_user_id"],
            ["public.profiles.user_id"],
            name="referrals_referrer_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["referred_user_id"],
            ["public.profiles.user_id"],
            name="referrals_referred_user_id_fkey",
            ondelete="SET NULL",
            use_alter=True,
        ),
        Index("idx_referrals_referrer_user_id", "referrer_user_id"),
        Index("idx_referrals_referred_user_id", "referred_user_id"),
        Index("idx_referrals_referral_code", "referral_code"),
        UniqueConstraint("referral_code", name="uq_referrals_referral_code"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The user who created/owns the referral code
    referrer_user_id = Column(UUID(as_uuid=True), nullable=False)

    # The user who used the referral code (nullable until used)
    referred_user_id = Column(UUID(as_uuid=True), nullable=True)

    # Unique referral code
    referral_code = Column(String, nullable=False, unique=True)

    # Status of the referral
    status = Column(
        Enum(ReferralStatus),
        nullable=False,
        default=ReferralStatus.PENDING,
    )

    # When the referral was completed (code was used)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Credits awarded to the referrer when referral completes
    credits_awarded_to_referrer = Column(Integer, nullable=False, default=0)

    # Credits awarded to the referred user when they sign up
    credits_awarded_to_referred = Column(Integer, nullable=False, default=0)

    # Timestamps
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
