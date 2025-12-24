"""
Referral Routes

API endpoints for managing user referrals.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common import global_config
from src.api.auth.unified_auth import get_authenticated_user_id
from src.api.auth.utils import user_uuid_from_str
from src.db.database import get_db_session
from src.db.models.public.profiles import Profiles
from src.db.models.public.referrals import (
    Referral,
    ReferralStatus,
    generate_referral_code,
)
from src.db.utils.db_transaction import db_transaction
from src.utils.logging_config import setup_logging

setup_logging()

router = APIRouter(prefix="/referrals", tags=["referrals"])


# Request/Response models
class ReferralCodeResponse(BaseModel):
    """Response containing a user's referral code."""

    referral_code: str
    created_at: str


class ApplyReferralRequest(BaseModel):
    """Request to apply a referral code."""

    referral_code: str


class ApplyReferralResponse(BaseModel):
    """Response after applying a referral code."""

    success: bool
    message: str
    credits_awarded: int


class ReferralStatsResponse(BaseModel):
    """Response containing referral statistics."""

    total_referrals: int
    completed_referrals: int
    pending_referrals: int
    total_credits_earned: int
    referral_code: str | None


class ReferralInfo(BaseModel):
    """Information about a single referral."""

    referred_user_email: str | None
    status: str
    credits_awarded: int
    completed_at: str | None
    created_at: str


class ReferralListResponse(BaseModel):
    """Response containing list of referrals."""

    referrals: list[ReferralInfo]
    total_count: int


def ensure_profile_exists(db: Session, user_uuid, email: str | None = None) -> Profiles:
    """Ensure a profile exists for the user, creating one if necessary."""
    profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()

    if not profile:
        logger.info(f"Creating new profile for user {user_uuid}")
        with db_transaction(db):
            profile = Profiles(
                user_id=user_uuid,
                email=email,
            )
            db.add(profile)

    return profile


@router.post("/code", response_model=ReferralCodeResponse)
async def create_referral_code(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ReferralCodeResponse:
    """
    Generate a new referral code for the authenticated user.

    If the user already has a referral code, returns the existing one.
    """
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)

    # Ensure profile exists
    ensure_profile_exists(db, user_uuid)

    # Check if user already has a referral code (a referral with no referred_user_id)
    existing_referral = (
        db.query(Referral)
        .filter(
            Referral.referrer_user_id == user_uuid,
            Referral.referred_user_id.is_(None),
            Referral.status == ReferralStatus.PENDING,
        )
        .first()
    )

    if existing_referral:
        logger.info(
            f"User {user_id} already has referral code: {existing_referral.referral_code}"
        )
        return ReferralCodeResponse(
            referral_code=existing_referral.referral_code,
            created_at=existing_referral.created_at.isoformat(),
        )

    # Generate a new unique referral code
    code_length = global_config.referral.code_length
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_referral_code(code_length)
        # Check if code already exists
        existing_code = (
            db.query(Referral).filter(Referral.referral_code == code).first()
        )
        if not existing_code:
            break
    else:
        logger.error(
            f"Failed to generate unique referral code after {max_attempts} attempts"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate unique referral code. Please try again.",
        )

    # Create the referral record
    with db_transaction(db):
        referral = Referral(
            referrer_user_id=user_uuid,
            referral_code=code,
            status=ReferralStatus.PENDING,
        )
        db.add(referral)

    logger.info(f"Created new referral code {code} for user {user_id}")

    return ReferralCodeResponse(
        referral_code=code,
        created_at=referral.created_at.isoformat(),
    )


@router.get("/code", response_model=ReferralCodeResponse)
async def get_referral_code(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ReferralCodeResponse:
    """
    Get the authenticated user's referral code.

    Returns 404 if the user doesn't have a referral code yet.
    """
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)

    # Find the user's pending referral code (one that hasn't been used yet)
    referral = (
        db.query(Referral)
        .filter(
            Referral.referrer_user_id == user_uuid,
            Referral.referred_user_id.is_(None),
            Referral.status == ReferralStatus.PENDING,
        )
        .first()
    )

    if not referral:
        raise HTTPException(
            status_code=404,
            detail="No referral code found. Use POST /referrals/code to create one.",
        )

    return ReferralCodeResponse(
        referral_code=referral.referral_code,
        created_at=referral.created_at.isoformat(),
    )


@router.post("/apply", response_model=ApplyReferralResponse)
async def apply_referral_code(
    request: Request,
    body: ApplyReferralRequest,
    db: Session = Depends(get_db_session),
) -> ApplyReferralResponse:
    """
    Apply a referral code for the authenticated user.

    The user can only apply a referral code once, and cannot use their own code.
    """
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)

    # Ensure profile exists
    profile = ensure_profile_exists(db, user_uuid)

    # Check if user has already used a referral code
    existing_referral = (
        db.query(Referral)
        .filter(
            Referral.referred_user_id == user_uuid,
            Referral.status == ReferralStatus.COMPLETED,
        )
        .first()
    )

    if existing_referral:
        raise HTTPException(
            status_code=400,
            detail="You have already used a referral code.",
        )

    # Find the referral code
    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_code == body.referral_code.upper(),
            Referral.status == ReferralStatus.PENDING,
            Referral.referred_user_id.is_(None),
        )
        .first()
    )

    if not referral:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired referral code.",
        )

    # Check if user is trying to use their own referral code
    if referral.referrer_user_id == user_uuid:
        raise HTTPException(
            status_code=400,
            detail="You cannot use your own referral code.",
        )

    # Get referral credits from config
    credits_for_referrer = global_config.referral.credits_for_referrer
    credits_for_referred = global_config.referral.credits_for_referred

    # Apply the referral
    with db_transaction(db):
        # Update the referral record
        referral.referred_user_id = user_uuid
        referral.status = ReferralStatus.COMPLETED
        referral.completed_at = datetime.now(timezone.utc)
        referral.credits_awarded_to_referrer = credits_for_referrer
        referral.credits_awarded_to_referred = credits_for_referred

        # Award credits to the referred user (current user)
        profile.credits = (profile.credits or 0) + credits_for_referred

        # Award credits to the referrer
        referrer_profile = (
            db.query(Profiles)
            .filter(Profiles.user_id == referral.referrer_user_id)
            .first()
        )
        if referrer_profile:
            referrer_profile.credits = (
                referrer_profile.credits or 0
            ) + credits_for_referrer

        # Create a new pending referral for the referrer so they can refer more people
        new_referral = Referral(
            referrer_user_id=referral.referrer_user_id,
            referral_code=generate_referral_code(global_config.referral.code_length),
            status=ReferralStatus.PENDING,
        )
        db.add(new_referral)

    logger.info(
        f"User {user_id} applied referral code {body.referral_code}. "
        f"Awarded {credits_for_referred} credits to referred user and "
        f"{credits_for_referrer} credits to referrer."
    )

    return ApplyReferralResponse(
        success=True,
        message=f"Referral code applied successfully! You received {credits_for_referred} credits.",
        credits_awarded=credits_for_referred,
    )


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ReferralStatsResponse:
    """
    Get referral statistics for the authenticated user.

    Returns the number of referrals, completed referrals, and total credits earned.
    """
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)

    # Get all referrals where this user is the referrer
    all_referrals = (
        db.query(Referral).filter(Referral.referrer_user_id == user_uuid).all()
    )

    # Count completed and pending referrals
    completed_referrals = [
        r for r in all_referrals if r.status == ReferralStatus.COMPLETED
    ]
    pending_referrals = [
        r
        for r in all_referrals
        if r.status == ReferralStatus.PENDING and r.referred_user_id is None
    ]

    # Calculate total credits earned from referrals
    total_credits = sum(r.credits_awarded_to_referrer for r in completed_referrals)

    # Get the user's current referral code (pending one with no referred user)
    current_code = next(
        (r.referral_code for r in pending_referrals),
        None,
    )

    return ReferralStatsResponse(
        total_referrals=len(completed_referrals),
        completed_referrals=len(completed_referrals),
        pending_referrals=len(pending_referrals),
        total_credits_earned=total_credits,
        referral_code=current_code,
    )


@router.get("/list", response_model=ReferralListResponse)
async def list_referrals(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ReferralListResponse:
    """
    List all referrals made by the authenticated user.

    Returns details about each referral including status and credits awarded.
    """
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)

    # Get all completed referrals where this user is the referrer
    referrals = (
        db.query(Referral)
        .filter(
            Referral.referrer_user_id == user_uuid,
            Referral.status == ReferralStatus.COMPLETED,
        )
        .order_by(Referral.completed_at.desc())
        .all()
    )

    # Build response with referred user emails
    referral_list = []
    for ref in referrals:
        # Get the referred user's email
        referred_profile = (
            db.query(Profiles).filter(Profiles.user_id == ref.referred_user_id).first()
        )
        referred_email = referred_profile.email if referred_profile else None

        referral_list.append(
            ReferralInfo(
                referred_user_email=referred_email,
                status=ref.status.value,
                credits_awarded=ref.credits_awarded_to_referrer,
                completed_at=ref.completed_at.isoformat() if ref.completed_at else None,
                created_at=ref.created_at.isoformat(),
            )
        )

    return ReferralListResponse(
        referrals=referral_list,
        total_count=len(referral_list),
    )
