"""Stripe webhook handlers."""

import json
from fastapi import APIRouter, HTTPException, Request, Depends
import stripe
from common import global_config
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from src.db.utils.db_transaction import db_transaction
from datetime import datetime, timezone
from src.api.routes.payments.stripe_config import INCLUDED_UNITS
from src.api.auth.utils import user_uuid_from_str

router = APIRouter()


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

        # Verify webhook signature
        # Use test webhook secret in dev, production secret in prod
        webhook_secret = (
            global_config.STRIPE_WEBHOOK_SECRET
            if global_config.DEV_ENV == "prod"
            else global_config.STRIPE_TEST_WEBHOOK_SECRET
        )

        if webhook_secret:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.SignatureVerificationError:
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            # If no webhook secret configured, parse payload directly (dev mode)
            event = json.loads(payload)

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

        # Verify webhook signature
        # Use test webhook secret in dev, production secret in prod
        webhook_secret = (
            global_config.STRIPE_WEBHOOK_SECRET
            if global_config.DEV_ENV == "prod"
            else global_config.STRIPE_TEST_WEBHOOK_SECRET
        )

        if webhook_secret:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.SignatureVerificationError:
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            # If no webhook secret configured, parse payload directly (dev mode)
            event = json.loads(payload)

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

            if not user_id:
                logger.warning(
                    "Subscription created event missing user_id metadata for subscription %s",
                    subscription_id,
                )
            else:
                user_uuid = user_uuid_from_str(user_id)

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

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing subscription webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
