"""Stripe webhook handlers."""

from datetime import datetime, timezone
from typing import Iterable

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from sqlalchemy.orm import Session

from common import global_config
from src.api.auth.utils import user_uuid_from_str
from src.api.routes.payments.stripe_config import INCLUDED_UNITS
from src.db.database import get_db_session
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.db.utils.db_transaction import db_transaction
from src.db.utils.users import ensure_profile_exists

router = APIRouter()


def _try_construct_event(payload: bytes, sig_header: str | None) -> dict:
    """
    Verify and construct the Stripe event using available secrets.

    Uses the environment-appropriate secret first, then falls back to the
    alternate secret if verification fails (helps when env vars are swapped).
    """

    def _secrets() -> Iterable[str]:
        primary = (
            global_config.STRIPE_WEBHOOK_SECRET
            if global_config.DEV_ENV == "prod"
            else global_config.STRIPE_TEST_WEBHOOK_SECRET
        )
        secondary = (
            global_config.STRIPE_TEST_WEBHOOK_SECRET
            if global_config.DEV_ENV == "prod"
            else global_config.STRIPE_WEBHOOK_SECRET
        )
        if primary:
            yield primary
        if secondary and secondary != primary:
            yield secondary

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    last_error: Exception | None = None
    for secret in _secrets():
        try:
            return stripe.Webhook.construct_event(payload, sig_header, secret)
        except Exception as exc:  # noqa: B902
            last_error = exc
            continue

    logger.error(f"Failed to verify Stripe webhook signature: {last_error}")
    raise HTTPException(status_code=400, detail="Invalid signature")


@router.post("/webhook/usage-reset")
async def handle_usage_reset_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Webhook endpoint to reset usage at the start of a new billing period.

    This should be called by Stripe webhook on 'invoice.payment_succeeded' event
    to reset usage counters when a new billing period starts.
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        # Verify webhook signature (tries primary, then alternate secret)
        event = _try_construct_event(payload, sig_header)

        # Handle invoice.payment_succeeded event
        if event.get("type") == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")

            if subscription_id:
                # Find user subscription by stripe_subscription_id
                subscription = (
                    db.query(UserSubscriptions)
                    .filter(UserSubscriptions.stripe_subscription_id == subscription_id)
                    .first()
                )

                if subscription:
                    # Reset usage for new billing period
                    with db_transaction(db):
                        subscription.current_period_usage = 0
                        subscription.billing_period_start = datetime.fromtimestamp(
                            invoice.get("period_start"), tz=timezone.utc
                        )
                        subscription.billing_period_end = datetime.fromtimestamp(
                            invoice.get("period_end"), tz=timezone.utc
                        )
                    logger.info(
                        f"Reset usage for subscription {subscription_id} on new billing period"
                    )

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/stripe")
async def handle_subscription_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Webhook endpoint to handle subscription lifecycle events.

    Handles events like:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        # Verify webhook signature (tries primary, then alternate secret)
        event = _try_construct_event(payload, sig_header)

        event_type = event.get("type")
        subscription_data = event["data"]["object"]
        subscription_id = subscription_data.get("id")

        logger.info(
            f"Received webhook event: {event_type} for subscription {subscription_id}"
        )

        if event_type == "customer.subscription.created":
            # Handle new subscription creation
            metadata = subscription_data.get("metadata", {})
            user_id = metadata.get("user_id")
            customer_id = subscription_data.get("customer")
            customer_email = None

            if customer_id:
                try:
                    customer = stripe.Customer.retrieve(
                        customer_id, api_key=stripe.api_key
                    )
                    customer_email = customer.get("email")
                except Exception as exc:  # noqa: B902
                    logger.warning(
                        "Unable to fetch customer %s for subscription %s: %s",
                        customer_id,
                        subscription_id,
                        exc,
                    )

            if not user_id:
                logger.warning(
                    "Subscription created event missing user_id metadata for subscription %s",
                    subscription_id,
                )
            else:
                user_uuid = user_uuid_from_str(user_id)
                ensure_profile_exists(db, user_uuid, customer_email, is_approved=True)

                # Extract subscription item ID (single item)
                subscription_item_id = None
                for item in subscription_data.get("items", {}).get("data", []):
                    subscription_item_id = item.get("id")
                    break

                # Update or create subscription record
                subscription = (
                    db.query(UserSubscriptions)
                    .filter(UserSubscriptions.user_id == user_uuid)
                    .first()
                )

                if subscription:
                    with db_transaction(db):
                        subscription.stripe_subscription_id = subscription_id
                        subscription.stripe_subscription_item_id = subscription_item_id
                        subscription.is_active = True
                        subscription.subscription_tier = "plus_tier"
                        subscription.included_units = INCLUDED_UNITS
                        subscription.billing_period_start = datetime.fromtimestamp(
                            subscription_data.get("current_period_start"),
                            tz=timezone.utc,
                        )
                        subscription.billing_period_end = datetime.fromtimestamp(
                            subscription_data.get("current_period_end"), tz=timezone.utc
                        )
                        subscription.current_period_usage = 0
                    logger.info(f"Updated subscription for user {user_uuid}")
                else:
                    # Create new subscription record
                    trial_start = subscription_data.get("trial_start")
                    new_subscription = UserSubscriptions(
                        user_id=user_uuid,
                        stripe_subscription_id=subscription_id,
                        stripe_subscription_item_id=subscription_item_id,
                        is_active=True,
                        subscription_tier="plus_tier",
                        included_units=INCLUDED_UNITS,
                        billing_period_start=datetime.fromtimestamp(
                            subscription_data.get("current_period_start"),
                            tz=timezone.utc,
                        ),
                        billing_period_end=datetime.fromtimestamp(
                            subscription_data.get("current_period_end"), tz=timezone.utc
                        ),
                        current_period_usage=0,
                        trial_start_date=(
                            datetime.fromtimestamp(trial_start, tz=timezone.utc)
                            if trial_start
                            else None
                        ),
                    )
                    with db_transaction(db):
                        db.add(new_subscription)
                    logger.info(f"Created subscription for user {user_uuid}")

        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription = (
                db.query(UserSubscriptions)
                .filter(UserSubscriptions.stripe_subscription_id == subscription_id)
                .first()
            )

            if subscription:
                with db_transaction(db):
                    subscription.is_active = False
                    subscription.subscription_tier = "free"
                    subscription.stripe_subscription_id = None
                    subscription.stripe_subscription_item_id = None
                    subscription.current_period_usage = 0
                logger.info(f"Deactivated subscription {subscription_id}")

        elif event_type == "invoice.payment_failed":
            # Handle payment failure -> auto-downgrade
            invoice_obj = event["data"]["object"]
            invoice_subscription_id = invoice_obj.get("subscription")

            if invoice_subscription_id:
                subscription = (
                    db.query(UserSubscriptions)
                    .filter(UserSubscriptions.stripe_subscription_id == invoice_subscription_id)
                    .first()
                )

                if subscription:
                    with db_transaction(db):
                        subscription.is_active = False
                        subscription.subscription_tier = "free"

                    logger.info(
                        f"Payment failed for subscription {invoice_subscription_id}. Downgraded to free."
                    )

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing subscription webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
