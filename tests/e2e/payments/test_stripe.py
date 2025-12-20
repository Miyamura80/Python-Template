import pytest
from sqlalchemy.orm import Session
from typing import Optional
import stripe
from datetime import datetime, timezone
import jwt
import json
import hmac
from hashlib import sha256

from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.db.models.stripe.subscription_types import (
    SubscriptionTier,
    PaymentStatus,
    SubscriptionStatus,
)
from tests.e2e.e2e_test_base import E2ETestBase
from common import global_config
from loguru import logger
from src.utils.logging_config import setup_logging

setup_logging(debug=True)

# Remove the is_prod check and always use test keys
stripe.api_key = global_config.STRIPE_TEST_SECRET_KEY

# Always use test price ID
STRIPE_PRICE_ID = global_config.subscription.stripe.price_ids.test


class TestSubscriptionE2E(E2ETestBase):

    async def cleanup_existing_subscription(
        self, auth_headers, db: Optional[Session] = None
    ):
        """Helper to clean up any existing subscription"""
        try:
            # Get user info from JWT token directly
            token = auth_headers["Authorization"].split(" ")[1]
            decoded = jwt.decode(
                token, algorithms=["HS256"], options={"verify_signature": False}
            )
            email = decoded.get("email")
            user_id = decoded.get("sub")

            if not email:
                raise Exception("No email found in JWT token")

            # Find and delete any existing subscriptions in Stripe
            customers = stripe.Customer.list(email=email, limit=1).data
            if customers:
                customer = customers[0]
                # Get all subscriptions for this customer
                subscriptions = stripe.Subscription.list(customer=customer.id)

                # Cancel all subscriptions
                for subscription in subscriptions.data:
                    logger.debug(f"Deleting Stripe subscription: {subscription.id}")
                    subscription.delete()

                # Then delete the customer
                logger.debug(f"Deleting Stripe customer: {customer.id}")
                customer.delete()

            # Also clean up database record if db session is provided
            if db and user_id:
                # Delete the subscription record entirely
                logger.debug(f"Deleting DB subscription for user {user_id}")
                db.query(UserSubscriptions).filter(
                    UserSubscriptions.user_id == user_id
                ).delete()
                db.commit()

        except Exception as e:
            logger.warning(f"Failed to cleanup subscription: {str(e)}")
            # Continue with the test even if cleanup fails

    @pytest.mark.asyncio
    async def test_create_checkout_session_e2e(self, db: Session, get_auth_headers):
        """Test creating a checkout session"""
        await self.cleanup_existing_subscription(get_auth_headers)

        response = self.client.post(
            "/checkout/create",
            headers={**get_auth_headers, "origin": "http://localhost:3000"},
        )

        assert response.status_code == 200
        assert "url" in response.json()
        assert response.json()["url"].startswith("https://checkout.stripe.com/")

    @pytest.mark.asyncio
    async def test_get_subscription_status_no_subscription_e2e(
        self, db: Session, get_auth_headers
    ):
        """Test getting subscription status when no subscription exists"""
        # Clean up any existing subscriptions first, passing the db session
        await self.cleanup_existing_subscription(get_auth_headers, db)
        db.commit()

        # Add debug logging to see what's in the database
        token = get_auth_headers["Authorization"].split(" ")[1]
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get("sub")

        db_subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )
        if db_subscription:
            logger.debug(
                f"Current DB state: active={db_subscription.is_active}, tier={db_subscription.subscription_tier}"
            )

        response = self.client.get("/subscription/status", headers=get_auth_headers)

        assert response.status_code == 200
        data = response.json()
        logger.debug(f"Response data: {data}")
        assert data["is_active"] is False
        assert data["subscription_tier"] == SubscriptionTier.FREE.value
        assert data["payment_status"] == PaymentStatus.NO_SUBSCRIPTION.value
        assert data["stripe_status"] is None
        assert data["source"] == "none"

    @pytest.mark.asyncio
    @pytest.mark.order(after="*")
    async def test_subscription_webhook_flow_e2e(self, db: Session, get_auth_headers):
        """Test the complete subscription flow through webhooks"""
        # Clean up any existing subscriptions first
        await self.cleanup_existing_subscription(get_auth_headers, db)

        # First create a customer in Stripe
        response = self.client.post(
            "/checkout/create",
            headers={**get_auth_headers, "origin": "http://localhost:3000"},
        )
        assert response.status_code == 200

        # Get user info from auth headers
        user = self.get_user_from_token(get_auth_headers["Authorization"].split(" ")[1])

        # Create a test subscription
        customer = stripe.Customer.list(email=user["email"], limit=1).data[0]
        # Update customer with user_id in metadata
        stripe.Customer.modify(customer.id, metadata={"user_id": user["id"]})
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": STRIPE_PRICE_ID}],
            trial_period_days=7,
        )

        # Create a simplified webhook event with minimal data
        current_time = int(datetime.now(timezone.utc).timestamp())
        trial_end = current_time + (7 * 24 * 60 * 60)  # 7 days from now

        event_data = {
            "id": "evt_test",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": subscription.id,
                    "object": "subscription",
                    "customer": customer.id,
                    "status": SubscriptionStatus.TRIALING.value,
                    "current_period_start": current_time,
                    "current_period_end": trial_end,
                    "trial_start": current_time,
                    "trial_end": trial_end,
                    "items": {"data": [{"price": {"id": STRIPE_PRICE_ID}}]},
                    "trial_settings": {
                        "end_behavior": {"missing_payment_method": "cancel"}
                    },
                    "billing_cycle_anchor": trial_end,
                    "cancel_at_period_end": False,
                    "metadata": {"user_id": user["id"]},
                }
            },
            "api_version": global_config.stripe.api_version,
            "created": current_time,
            "livemode": False,
        }

        # Generate signature
        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload = json.dumps(event_data)
        signed_payload = f"{timestamp}.{payload}"

        # Compute signature using the webhook secret
        mac = hmac.new(
            global_config.STRIPE_TEST_WEBHOOK_SECRET.encode("utf-8"),
            msg=signed_payload.encode("utf-8"),
            digestmod=sha256,
        )
        signature = mac.hexdigest()

        # Send webhook event - use payload directly instead of letting FastAPI serialize again
        webhook_response = self.client.post(
            "/webhook/stripe",
            headers={
                "stripe-signature": f"t={timestamp},v1={signature}",
                "Content-Type": "application/json",
            },
            content=payload,  # Use the pre-serialized payload
        )

        logger.debug(
            f"Webhook response: {webhook_response.status_code} {webhook_response.json()}"
        )

        assert webhook_response.status_code == 200

        # Verify subscription was recorded in database
        db_subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user["id"])
            .first()
        )

        assert db_subscription is not None
        assert db_subscription.is_active is True
        assert db_subscription.subscription_tier == SubscriptionTier.PLUS.value
        assert db_subscription.trial_start_date is not None

        # Check subscription status endpoint
        status_response = self.client.get("/subscription/status", headers=get_auth_headers)

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["is_active"] is True
        assert status_data["subscription_tier"] == SubscriptionTier.PLUS.value
        assert status_data["payment_status"] == PaymentStatus.ACTIVE.value
        assert status_data["source"] == "stripe"

    @pytest.mark.asyncio
    async def test_cancel_subscription_e2e(self, db: Session, get_auth_headers):
        """Test cancelling a subscription"""
        # Clean up first to ensure we start fresh
        await self.cleanup_existing_subscription(get_auth_headers, db)
        db.commit()

        # Now create new subscription
        await self.test_subscription_webhook_flow_e2e(db, get_auth_headers)

        # Then test cancellation
        response = self.client.post("/cancel_subscription", headers=get_auth_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify subscription status
        status_response = self.client.get("/subscription/status", headers=get_auth_headers)

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["is_active"] is False
        assert status_data["subscription_tier"] == SubscriptionTier.FREE.value
