"""Stripe webhook handlers."""

import json
from fastapi import APIRouter, HTTPException, Request, Depends
import stripe
from common import global_config
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from datetime import datetime, timezone
from src.api.routes.payments.stripe_config import INCLUDED_UNITS

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
        webhook_secret = getattr(global_config, "STRIPE_WEBHOOK_SECRET", None)

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
                    subscription.current_period_usage = 0
                    subscription.billing_period_start = datetime.fromtimestamp(
                        invoice.get("period_start"), tz=timezone.utc
                    )
                    subscription.billing_period_end = datetime.fromtimestamp(
                        invoice.get("period_end"), tz=timezone.utc
                    )
                    db.commit()
                    logger.info(
                        f"Reset usage for subscription {subscription_id} on new billing period"
                    )

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/subscription")
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
        webhook_secret = getattr(global_config, "STRIPE_WEBHOOK_SECRET", None)

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

            if user_id:
                # Extract subscription item ID (single item)
                subscription_item_id = None
                for item in subscription_data.get("items", {}).get("data", []):
                    subscription_item_id = item.get("id")
                    break

                # Update or create subscription record
                subscription = (
                    db.query(UserSubscriptions)
                    .filter(UserSubscriptions.user_id == user_id)
                    .first()
                )

                if subscription:
                    subscription.stripe_subscription_id = subscription_id
                    subscription.stripe_subscription_item_id = subscription_item_id
                    subscription.is_active = True
                    subscription.subscription_tier = "plus_tier"
                    subscription.included_units = INCLUDED_UNITS
                    subscription.billing_period_start = datetime.fromtimestamp(
                        subscription_data.get("current_period_start"), tz=timezone.utc
                    )
                    subscription.billing_period_end = datetime.fromtimestamp(
                        subscription_data.get("current_period_end"), tz=timezone.utc
                    )
                    subscription.current_period_usage = 0
                    db.commit()
                    logger.info(f"Updated subscription for user {user_id}")

        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription = (
                db.query(UserSubscriptions)
                .filter(UserSubscriptions.stripe_subscription_id == subscription_id)
                .first()
            )

            if subscription:
                subscription.is_active = False
                subscription.subscription_tier = "free"
                subscription.stripe_subscription_id = None
                subscription.stripe_subscription_item_id = None
                subscription.current_period_usage = 0
                db.commit()
                logger.info(f"Deactivated subscription {subscription_id}")

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing subscription webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
