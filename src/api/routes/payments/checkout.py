"""Checkout and subscription management endpoints."""

from fastapi import APIRouter, Header, HTTPException, Request, Depends
import stripe
from common import global_config
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from src.db.utils.db_transaction import db_transaction
from datetime import datetime, timezone
from src.api.auth.workos_auth import get_current_workos_user
from src.api.routes.payments.stripe_config import STRIPE_PRICE_ID

router = APIRouter()


@router.post("/checkout/create")
async def create_checkout(request: Request, authorization: str = Header(None)):
    """Create a Stripe checkout session for subscription."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # User authentication using WorkOS
        workos_user = await get_current_workos_user(request)
        email = workos_user.email
        user_id = workos_user.id
        logger.debug(f"Authenticated user: {email} (ID: {user_id})")

        if not email:
            raise HTTPException(status_code=400, detail="No email found for user")

        # Log Stripe configuration
        logger.debug(f"Using Stripe API key for {global_config.DEV_ENV} environment")
        logger.debug(f"Price ID: {STRIPE_PRICE_ID}")

        # Check existing customer
        logger.debug(f"Checking for existing Stripe customer with email: {email}")
        customers = stripe.Customer.list(
            email=email,
            limit=1,
            api_key=stripe.api_key,
        )

        customer_id = None
        if customers["data"]:
            customer_id = customers["data"][0]["id"]
            # Update existing customer with user_id if needed
            stripe.Customer.modify(
                customer_id, metadata={"user_id": user_id}, api_key=stripe.api_key
            )
        else:
            # Create new customer with user_id in metadata
            customer = stripe.Customer.create(
                email=email, metadata={"user_id": user_id}, api_key=stripe.api_key
            )
            customer_id = customer.id

        # Check active subscriptions
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="all",
            limit=1,
            api_key=stripe.api_key,
        )

        # Check if already subscribed
        if subscriptions["data"]:
            sub = subscriptions["data"][0]
            logger.debug(f"Found existing subscription with status: {sub['status']}")
            if sub["status"] in ["active", "trialing"]:
                logger.debug(f"Subscription already exists and is {sub['status']}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Already subscribed",
                        "status": sub["status"],
                        "subscription_id": sub["id"],
                    },
                )

        # Verify origin
        base_url = request.headers.get("origin")
        logger.debug(f"Received origin header: {base_url}")
        if not base_url:
            raise HTTPException(status_code=400, detail="Origin header is required")

        logger.debug(f"Creating checkout session with price: {STRIPE_PRICE_ID}")

        # Single metered price - no quantity for metered prices
        line_items = [{"price": STRIPE_PRICE_ID}]

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            customer_email=None if customer_id else email,
            line_items=line_items,
            mode="subscription",
            subscription_data={
                "trial_period_days": global_config.subscription.trial_period_days,
                "metadata": {"user_id": user_id},
            },
            success_url=f"{base_url}/subscription/success",
            cancel_url=f"{base_url}/subscription/pricing",
            api_key=stripe.api_key,
        )

        logger.debug("Checkout session created successfully")
        return {"url": session.url}

    except HTTPException as e:
        logger.error(f"HTTP Exception in create_checkout: {str(e.detail)}")
        raise
    except stripe.StripeError as e:
        logger.error(f"Stripe error in create_checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_checkout: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/cancel_subscription")
async def cancel_subscription(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db_session),
):
    """Cancel the user's active subscription."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # Get user using WorkOS
        workos_user = await get_current_workos_user(request)
        email = workos_user.email
        user_id = workos_user.id

        if not email:
            raise HTTPException(status_code=400, detail="No email found for user")

        # Find customer
        customers = stripe.Customer.list(email=email, limit=1, api_key=stripe.api_key)

        if not customers["data"]:
            logger.debug(f"No subscription found for email: {email}")
            return {"status": "success", "message": "No active subscription to cancel"}

        customer_id = customers["data"][0]["id"]

        # Find active subscription
        subscriptions = stripe.Subscription.list(
            customer=customer_id, status="all", limit=1, api_key=stripe.api_key
        )

        if not subscriptions["data"] or not any(
            sub["status"] in ["active", "trialing"] for sub in subscriptions["data"]
        ):
            logger.debug(
                f"No active or trialing subscription found for customer: {customer_id}, {email}"
            )
            return {"status": "success", "message": "No active subscription to cancel"}

        # Cancel subscription in Stripe
        subscription_id = subscriptions["data"][0]["id"]
        cancelled_subscription = stripe.Subscription.delete(
            subscription_id, api_key=stripe.api_key
        )

        # Update subscription in database
        subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )

        if subscription:
            with db_transaction(db):
                subscription.is_active = False
                subscription.auto_renew = False
                subscription.subscription_tier = "free"
                subscription.subscription_end_date = datetime.fromtimestamp(
                    cancelled_subscription.current_period_end, tz=timezone.utc
                )
                # Reset usage tracking
                subscription.current_period_usage = 0
                subscription.stripe_subscription_id = None
                subscription.stripe_subscription_item_id = None
            logger.info(f"Updated subscription status in database for user {user_id}")

        logger.info(
            f"Successfully cancelled subscription {subscription_id} for customer {customer_id}"
        )
        return {"status": "success", "message": "Subscription cancelled"}

    except stripe.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription/success")
async def subscription_success():
    """Handle successful subscription redirect."""
    return {"status": "success", "message": "Subscription activated successfully"}


@router.get("/subscription/pricing")
async def subscription_pricing():
    """Handle cancelled subscription redirect."""
    return {"status": "cancelled", "message": "Subscription checkout was cancelled"}
