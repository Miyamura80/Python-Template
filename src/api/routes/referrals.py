from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.api.auth.unified_auth import authenticated_user
from src.db.models.public.profiles import Profiles
from src.api.services.referral_service import ReferralService
from src.db.utils.users import ensure_profile_exists
from typing import Dict

router = APIRouter(prefix="/referrals", tags=["Referrals"])

class ReferralApplyRequest(BaseModel):
    referral_code: str

class ReferralResponse(BaseModel):
    referral_code: str
    referral_count: int
    referrer_id: str | None = None

@router.post("/apply", response_model=Dict[str, str])
def apply_referral(
    payload: ReferralApplyRequest,
    user=Depends(authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Apply a referral code to the current user.
    """
    # Ensure profile exists
    profile = ensure_profile_exists(db, user.id, user.email)

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
def get_referral_code(
    user=Depends(authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's referral code and stats.
    """
    profile = ensure_profile_exists(db, user.id, user.email)

    return ReferralResponse(
        referral_code=profile.referral_code,
        referral_count=profile.referral_count,
        referrer_id=str(profile.referrer_id) if profile.referrer_id else None
    )
