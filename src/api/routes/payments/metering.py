"""Usage metering and tracking endpoints."""

from fastapi import APIRouter, Header, HTTPException, Request, Depends
import stripe
import time
from loguru import logger
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from sqlalchemy.orm import Session
from src.db.database import get_db_session
from src.db.utils.db_transaction import db_transaction
from pydantic import BaseModel
from src.db.models.stripe.subscription_types import UsageAction
from src.api.auth.workos_auth import get_current_workos_user
from src.api.routes.payments.stripe_config import (
    INCLUDED_UNITS,
    OVERAGE_UNIT_AMOUNT,
)

router = APIRouter()


# Pydantic models for request/response
class UsageReportRequest(BaseModel):
    """Request model for reporting usage."""

    quantity: int
    action: UsageAction = UsageAction.INCREMENT
    idempotency_key: str | None = None


class UsageResponse(BaseModel):
    """Response model for usage data."""

    current_usage: int
    included_units: int
    overage_units: int
    billing_period_start: str | None
    billing_period_end: str | None
    estimated_overage_cost: float


@router.post("/usage/report")
async def report_usage(
    request: Request,
    usage_request: UsageReportRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db_session),
):
    """
    Report usage for metered billing.

    Reports ALL usage to Stripe. If using graduated tiered pricing,
    Stripe automatically handles the free tier (included units).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # User authentication using WorkOS
        workos_user = await get_current_workos_user(request)
        user_id = workos_user.id

        # Get subscription from database
        subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )

        if not subscription or not subscription.is_active:
            raise HTTPException(status_code=400, detail="No active subscription found")

        if not subscription.stripe_subscription_item_id:
            raise HTTPException(
                status_code=400,
                detail="No subscription item found. Please check subscription status first.",
            )

        # Calculate new usage based on action
        current_usage = subscription.current_period_usage or 0
        if usage_request.action == UsageAction.SET:
            new_usage = usage_request.quantity
        else:  # INCREMENT
            new_usage = current_usage + usage_request.quantity

        # Report ALL usage to Stripe (graduated tiers handle free tier automatically)
        usage_record_params = {
            "quantity": new_usage,
            "timestamp": int(time.time()),
            "action": "set",  # Set to total usage amount
        }

        if usage_request.idempotency_key:
            stripe.SubscriptionItem.create_usage_record(
                subscription.stripe_subscription_item_id,
                **usage_record_params,
                api_key=stripe.api_key,
                idempotency_key=usage_request.idempotency_key,
            )
        else:
            stripe.SubscriptionItem.create_usage_record(
                subscription.stripe_subscription_item_id,
                **usage_record_params,
                api_key=stripe.api_key,
            )

        # Update local usage cache
        with db_transaction(db):
            subscription.current_period_usage = new_usage

        # Calculate overage for display (Stripe handles actual billing)
        overage = max(0, new_usage - INCLUDED_UNITS)

        logger.info(
            f"Usage reported for user {user_id}: {new_usage} total "
            f"({INCLUDED_UNITS} included, {overage} overage)"
        )

        return {
            "status": "success",
            "current_usage": new_usage,
            "included_units": INCLUDED_UNITS,
            "overage_units": overage,
            "estimated_overage_cost": overage * OVERAGE_UNIT_AMOUNT / 100,
        }

    except HTTPException:
        raise
    except stripe.StripeError as e:
        logger.error(f"Stripe error reporting usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error reporting usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/current", response_model=UsageResponse)
async def get_current_usage(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db_session),
):
    """
    Get current usage for the authenticated user's subscription.

    Returns usage data including current usage, included units, overage, and estimated costs.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization header")

    try:
        # User authentication using WorkOS
        workos_user = await get_current_workos_user(request)
        user_id = workos_user.id

        # Get subscription from database
        subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )

        if not subscription:
            return UsageResponse(
                current_usage=0,
                included_units=INCLUDED_UNITS,
                overage_units=0,
                billing_period_start=None,
                billing_period_end=None,
                estimated_overage_cost=0.0,
            )

        current_usage = subscription.current_period_usage or 0
        included = subscription.included_units or INCLUDED_UNITS
        overage = max(0, current_usage - included)

        return UsageResponse(
            current_usage=current_usage,
            included_units=included,
            overage_units=overage,
            billing_period_start=(
                subscription.billing_period_start.isoformat()
                if subscription.billing_period_start
                else None
            ),
            billing_period_end=(
                subscription.billing_period_end.isoformat()
                if subscription.billing_period_end
                else None
            ),
            estimated_overage_cost=overage * OVERAGE_UNIT_AMOUNT / 100,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
