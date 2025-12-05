from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    BigInteger,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from src.db.models import Base
import uuid


class UserSubscriptions(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["public.profiles.user_id"],
            name="user_subscriptions_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,  # Defer foreign key creation to break circular dependency
        ),
        {"schema": "public"},
    )

    # Row-Level Security (RLS) policies
    # Temporarily removed for WorkOS migration - will add custom auth schema later
    # __rls_policies__ = {
    #     "user_can_view_subscription": {
    #         "command": "SELECT",
    #         "using": "user_id = auth.uid()",
    #     }
    # }

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    trial_start_date = Column(TIMESTAMP, nullable=True)
    subscription_start_date = Column(TIMESTAMP, nullable=True)
    subscription_end_date = Column(TIMESTAMP, nullable=True)
    subscription_tier = Column(String, nullable=True)  # e.g., "free" or "plus_tier"
    is_active = Column(Boolean, nullable=False, default=False)
    renewal_date = Column(TIMESTAMP, nullable=True)
    auto_renew = Column(Boolean, nullable=False, default=True)
    payment_failure_count = Column(Integer, nullable=False, default=0)
    last_payment_failure = Column(TIMESTAMP, nullable=True)

    # Stripe subscription IDs for metered billing
    stripe_subscription_id = Column(String, nullable=True)
    stripe_subscription_item_id = Column(String, nullable=True)  # Single metered item

    # Usage tracking for metered billing (local cache)
    current_period_usage = Column(BigInteger, nullable=False, default=0)
    included_units = Column(BigInteger, nullable=False, default=0)
    billing_period_start = Column(TIMESTAMP, nullable=True)
    billing_period_end = Column(TIMESTAMP, nullable=True)
