from fastapi import APIRouter, Header, HTTPException, Request, Depends
import stripe
from common import global_config
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from datetime import datetime, timezone
from src.db.models.stripe.subscription_types import (
    SubscriptionTier,
    PaymentStatus,
)
from src.api.auth.workos_auth import get_current_workos_user

router = APIRouter()

# Initialize Stripe with test credentials in dev mode
# Use test key in dev, production key in prod
stripe.api_key = (
    global_config.STRIPE_SECRET_KEY
    if global_config.DEV_ENV == "prod"
    else global_config.STRIPE_TEST_SECRET_KEY
)
stripe.api_version = getattr(global_config.subscription, "api_version", "2024-11-20.acacia")

# Use appropriate price ID based on environment
STRIPE_PRICE_ID = global_config.subscription.stripe.price_ids.test

# Verify the price in test mode
try:
    price = stripe.Price.retrieve(STRIPE_PRICE_ID, api_key=stripe.api_key)
    logger.debug(f"Test price verified: {price.id} (livemode: {price.livemode})")
except Exception as e:
    logger.error(f"Error verifying test price: {str(e)}")
    raise


@router.post("/checkout/create")
async def create_checkout(request: Request, authorization: str = Header(None)):
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
        logger.debug(f"Price ID being used: {STRIPE_PRICE_ID}")

        # Check existing customer in test mode
        logger.debug(f"Checking for existing Stripe customer with email: {email}")
        customers = stripe.Customer.list(
            email=email,
            limit=1,
            api_key=stripe.api_key,  # Use the configured api_key instead of explicitly using test key
        )

        customer_id = None
        if customers["data"]:
            customer_id = customers["data"][0]["id"]
            # Update existing customer with user_id if needed
            customer = stripe.Customer.modify(
                customer_id, metadata={"user_id": user_id}, api_key=stripe.api_key
            )
        else:
            # Create new customer with user_id in metadata
            customer = stripe.Customer.create(
                email=email, metadata={"user_id": user_id}, api_key=stripe.api_key
            )
            customer_id = customer.id

        # Check active subscriptions in test mode
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="all",  # Get all subscriptions
            price=STRIPE_PRICE_ID,
            limit=1,
            api_key=stripe.api_key,
        )

        # More detailed subscription status check
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

        logger.debug(f"Creating checkout session with price_id: {STRIPE_PRICE_ID}")
        logger.debug(f"Using base_url: {base_url}")

        # Create checkout session in test mode
        session = stripe.checkout.Session.create(
            customer=customer_id,
            customer_email=None if customer_id else email,
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            subscription_data={
                "trial_period_days": global_config.subscription.trial_period_days
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
    db: Session = Depends(get_db_session),  # Add database dependency
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # Get user using WorkOS
        workos_user = await get_current_workos_user(request)
        email = workos_user.email
        user_id = workos_user.id  # Get user_id for database update

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
            subscription.is_active = False
            subscription.auto_renew = False
            subscription.subscription_tier = "free"
            subscription.subscription_end_date = datetime.fromtimestamp(
                cancelled_subscription.current_period_end, tz=timezone.utc
            )
            db.commit()
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
async def subscription_cancel():
    """Handle cancelled subscription redirect."""
    return {"status": "cancelled", "message": "Subscription checkout was cancelled"}


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

        if not email:
            raise HTTPException(status_code=400, detail="No email found for user")

        # Find customer in Stripe
        customers = stripe.Customer.list(email=email, limit=1, api_key=stripe.api_key)

        if customers["data"]:
            customer_id = customers["data"][0]["id"]

            # Get latest subscription with price filter
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="all",
                price=STRIPE_PRICE_ID,
                limit=1,
                expand=["data.latest_invoice"],
                api_key=stripe.api_key,
            )

            if subscriptions["data"]:
                subscription = subscriptions["data"][0]

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
                }

        # Fallback to database check if no Stripe subscription found
        db_subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )

        if db_subscription:
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
            }

        # No subscription found in either Stripe or database
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
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error checking subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
