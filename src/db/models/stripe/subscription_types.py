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
