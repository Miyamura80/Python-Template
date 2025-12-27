from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db_session
from src.api.auth.unified_auth import get_authenticated_user
from src.api.services.referral_service import ReferralService
from src.db.utils.users import ensure_profile_exists
from src.api.auth.utils import user_uuid_from_str
from typing import Dict, cast

router = APIRouter(prefix="/referrals", tags=["Referrals"])


class ReferralApplyRequest(BaseModel):
    referral_code: str


class ReferralResponse(BaseModel):
    referral_code: str
    referral_count: int
    referrer_id: str | None = None


@router.post("/apply", response_model=Dict[str, str])
async def apply_referral(
    request: Request,
    payload: ReferralApplyRequest,
    db: Session = Depends(get_db_session),
):
    """
    Apply a referral code to the current user.
    """
    user = await get_authenticated_user(request, db)
    user_uuid = user_uuid_from_str(user.id)

    # Ensure profile exists
    profile = ensure_profile_exists(db, user_uuid, user.email)

    success = ReferralService.apply_referral(db, profile, payload.referral_code)

    if not success:
        # Check why it failed
        if profile.referrer_id:
            raise HTTPException(status_code=400, detail="User already has a referrer")

        referrer = ReferralService.validate_referral_code(db, payload.referral_code)
        if not referrer:
            raise HTTPException(status_code=404, detail="Invalid referral code")

        if referrer.user_id == profile.user_id:
            raise HTTPException(status_code=400, detail="Cannot refer yourself")

        raise HTTPException(status_code=400, detail="Failed to apply referral code")

    return {"message": "Referral code applied successfully"}


@router.get("/code", response_model=ReferralResponse)
async def get_referral_code(request: Request, db: Session = Depends(get_db_session)):
    """
    Get the current user's referral code and stats.
    Generates a code if one doesn't exist.
    """
    user = await get_authenticated_user(request, db)
    user_uuid = user_uuid_from_str(user.id)

    profile = ensure_profile_exists(db, user_uuid, user.email)

    # Lazy generation of referral code if not present
    referral_code = ReferralService.get_or_create_referral_code(db, profile)

    return ReferralResponse(
        referral_code=str(referral_code),
        referral_count=cast(int, profile.referral_count or 0),
        referrer_id=str(profile.referrer_id) if profile.referrer_id else None,
    )
