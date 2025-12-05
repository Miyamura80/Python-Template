from enum import Enum


class SubscriptionTier(str, Enum):
    """Subscription tier types"""

    FREE = "free"
    PLUS = "plus_tier"  # Matches current implementation


class SubscriptionStatus(str, Enum):
    """Subscription status types from Stripe"""

    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"


class PaymentStatus(str, Enum):
    """Payment status types"""

    ACTIVE = "active"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_FAILED_FINAL = "payment_failed_final"
    NO_SUBSCRIPTION = "no_subscription"


class UsageAction(str, Enum):
    """Usage record action types for metered billing"""

    INCREMENT = "increment"  # Add to existing usage
    SET = "set"  # Replace existing usage with new value


class BillingType(str, Enum):
    """Types of billing for subscription items"""

    FIXED = "fixed"  # Fixed recurring price
    METERED = "metered"  # Usage-based metered price
