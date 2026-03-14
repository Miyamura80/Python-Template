"""Subscription status endpoint."""

from fastapi import APIRouter, Header, HTTPException, Request, Depends
import stripe
from common import global_config
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from src.db.utils.db_transaction import db_transaction
from datetime import datetime, timezone
from src.db.models.stripe.subscription_types import (
    SubscriptionTier,
    PaymentStatus,
)
from src.api.auth.workos_auth import get_current_workos_user
from src.api.routes.payments.stripe_config import (
    INCLUDED_UNITS,
    OVERAGE_UNIT_AMOUNT,
    UNIT_LABEL,
)
from src.api.auth.utils import user_uuid_from_str
from src.db.utils.users import ensure_profile_exists

router = APIRouter()


@router.get("/subscription/status")
async def get_subscription_status(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db_session),
):
    """Get the current subscription status from Stripe for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # User authentication using WorkOS
        workos_user = await get_current_workos_user(request)
        email = workos_user.email
        user_id = workos_user.id
        user_uuid = user_uuid_from_str(user_id)

        if not email:
            raise HTTPException(status_code=400, detail="No email found for user")

        # Ensure profile exists before creating subscription
        ensure_profile_exists(db, user_uuid, email)

        # Find customer in Stripe
        customers = stripe.Customer.list(email=email, limit=1, api_key=stripe.api_key)

        if customers["data"]:
            customer_id = customers["data"][0]["id"]

            # Get latest subscription
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="all",
                limit=1,
                expand=["data.latest_invoice", "data.items.data"],
                api_key=stripe.api_key,
            )

            if subscriptions["data"]:
                subscription = subscriptions["data"][0]

                # Extract subscription item ID (single metered item)
                subscription_item_id = None
                for item in subscription.get("items", {}).get("data", []):
                    subscription_item_id = item.get("id")
                    break  # Use the first (and should be only) item

                # Update database with subscription info
                db_subscription = (
                    db.query(UserSubscriptions)
                    .filter(UserSubscriptions.user_id == user_uuid)
                    .first()
                )

                if db_subscription:
                    with db_transaction(db):
                        db_subscription.stripe_subscription_id = subscription.id
                        db_subscription.stripe_subscription_item_id = (
                            subscription_item_id
                        )
                        db_subscription.billing_period_start = datetime.fromtimestamp(
                            subscription.current_period_start, tz=timezone.utc
                        )
                        db_subscription.billing_period_end = datetime.fromtimestamp(
                            subscription.current_period_end, tz=timezone.utc
                        )
                        db_subscription.included_units = INCLUDED_UNITS
                        db_subscription.is_active = subscription.status in [
                            "active",
                            "trialing",
                        ]
                        db_subscription.subscription_tier = (
                            SubscriptionTier.PLUS.value
                            if db_subscription.is_active
                            else SubscriptionTier.FREE.value
                        )
                        db_subscription.subscription_start_date = (
                            datetime.fromtimestamp(
                                subscription.start_date, tz=timezone.utc
                            )
                        )
                        db_subscription.subscription_end_date = datetime.fromtimestamp(
                            subscription.current_period_end, tz=timezone.utc
                        )
                        db_subscription.renewal_date = datetime.fromtimestamp(
                            subscription.current_period_end, tz=timezone.utc
                        )
                else:
                    with db_transaction(db):
                        db_subscription = UserSubscriptions(
                            user_id=user_uuid,
                            stripe_subscription_id=subscription.id,
                            stripe_subscription_item_id=subscription_item_id,
                            billing_period_start=datetime.fromtimestamp(
                                subscription.current_period_start, tz=timezone.utc
                            ),
                            billing_period_end=datetime.fromtimestamp(
                                subscription.current_period_end, tz=timezone.utc
                            ),
                            included_units=INCLUDED_UNITS,
                            is_active=subscription.status
                            in [
                                "active",
                                "trialing",
                            ],
                            subscription_tier=(
                                SubscriptionTier.PLUS.value
                                if subscription.status in ["active", "trialing"]
                                else SubscriptionTier.FREE.value
                            ),
                            subscription_start_date=datetime.fromtimestamp(
                                subscription.start_date, tz=timezone.utc
                            ),
                            subscription_end_date=datetime.fromtimestamp(
                                subscription.current_period_end, tz=timezone.utc
                            ),
                            renewal_date=datetime.fromtimestamp(
                                subscription.current_period_end, tz=timezone.utc
                            ),
                            current_period_usage=0,
                        )
                        db.add(db_subscription)

                # Determine payment status
                payment_status = (
                    PaymentStatus.ACTIVE.value
                    if subscription.status in ["active", "trialing"]
                    else PaymentStatus.NO_SUBSCRIPTION.value
                )
                payment_failure_count = 0
                last_payment_failure = None

                if (
                    subscription.latest_invoice
                    and subscription.latest_invoice.status == "open"
                ):
                    payment_status = PaymentStatus.PAYMENT_FAILED.value
                    payment_failure_count = subscription.latest_invoice.attempt_count
                    if (
                        payment_failure_count
                        >= global_config.subscription.payment_retry.max_attempts
                    ):
                        payment_status = PaymentStatus.PAYMENT_FAILED_FINAL.value
                    if subscription.latest_invoice.created:
                        last_payment_failure = datetime.fromtimestamp(
                            subscription.latest_invoice.created, tz=timezone.utc
                        ).isoformat()

                # Get usage info
                current_usage = (
                    db_subscription.current_period_usage if db_subscription else 0
                )
                overage = max(0, current_usage - INCLUDED_UNITS)

                return {
                    "is_active": subscription.status in ["active", "trialing"],
                    "subscription_tier": (
                        SubscriptionTier.PLUS.value
                        if subscription.status in ["active", "trialing"]
                        else SubscriptionTier.FREE.value
                    ),
                    "subscription_start_date": datetime.fromtimestamp(
                        subscription.start_date, tz=timezone.utc
                    ).isoformat(),
                    "subscription_end_date": datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    ).isoformat(),
                    "renewal_date": datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    ).isoformat(),
                    "payment_status": payment_status,
                    "payment_failure_count": payment_failure_count,
                    "last_payment_failure": last_payment_failure,
                    "stripe_status": subscription.status,
                    "source": "stripe",
                    # Usage info
                    "usage": {
                        "current_usage": current_usage,
                        "included_units": INCLUDED_UNITS,
                        "overage_units": overage,
                        "unit_label": UNIT_LABEL,
                        "estimated_overage_cost": overage * OVERAGE_UNIT_AMOUNT / 100,
                    },
                }

        # Fallback to database check if no Stripe subscription found
        db_subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_uuid)
            .first()
        )

        if db_subscription:
            current_usage = db_subscription.current_period_usage or 0
            overage = max(0, current_usage - INCLUDED_UNITS)

            return {
                "is_active": db_subscription.is_active,
                "subscription_tier": db_subscription.subscription_tier,
                "subscription_start_date": (
                    db_subscription.subscription_start_date.isoformat()
                    if db_subscription.subscription_start_date
                    else None
                ),
                "subscription_end_date": (
                    db_subscription.subscription_end_date.isoformat()
                    if db_subscription.subscription_end_date
                    else None
                ),
                "renewal_date": (
                    db_subscription.subscription_end_date.isoformat()
                    if db_subscription.subscription_end_date
                    else None
                ),
                "payment_status": (
                    PaymentStatus.ACTIVE.value
                    if db_subscription.is_active
                    else PaymentStatus.NO_SUBSCRIPTION.value
                ),
                "payment_failure_count": 0,
                "last_payment_failure": None,
                "stripe_status": None,
                "source": "database",
                # Usage info
                "usage": {
                    "current_usage": current_usage,
                    "included_units": db_subscription.included_units or INCLUDED_UNITS,
                    "overage_units": overage,
                    "unit_label": UNIT_LABEL,
                    "estimated_overage_cost": overage * OVERAGE_UNIT_AMOUNT / 100,
                },
            }

        # No subscription found
        return {
            "is_active": False,
            "subscription_tier": SubscriptionTier.FREE.value,
            "subscription_start_date": None,
            "subscription_end_date": None,
            "renewal_date": None,
            "payment_status": PaymentStatus.NO_SUBSCRIPTION.value,
            "payment_failure_count": 0,
            "last_payment_failure": None,
            "stripe_status": None,
            "source": "none",
            # Usage info
            "usage": {
                "current_usage": 0,
                "included_units": INCLUDED_UNITS,
                "overage_units": 0,
                "unit_label": UNIT_LABEL,
                "estimated_overage_cost": 0.0,
            },
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error checking subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
