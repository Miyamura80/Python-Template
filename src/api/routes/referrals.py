"""Referral routes.

This module implements a simple referral system that works with the existing
WorkOS/Auth setup by storing referral state on `public.profiles`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger as log
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common import global_config
from src.api.auth.unified_auth import get_authenticated_user
from src.api.auth.utils import user_uuid_from_str
from src.db.database import get_db_session
from src.db.models.public.profiles import Profiles
from src.db.utils.db_transaction import db_transaction
from src.utils.logging_config import setup_logging


setup_logging()

router = APIRouter()

_REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_MAX_CODE_ATTEMPTS = 25


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_referral_code(code: str) -> str:
    return code.strip().upper()


def _generate_referral_code(length: int) -> str:
    return "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(length))


def _ensure_profile_exists(db: Session, user_uuid, email: str | None) -> Profiles:
    profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()
    if profile:
        return profile

    log.info("Creating new profile for referral flow | user_id=%s", user_uuid)
    with db_transaction(db):
        profile = Profiles(
            user_id=user_uuid,
            email=email,
        )
        db.add(profile)
    return profile


def _ensure_referral_code(db: Session, profile: Profiles) -> str:
    if profile.referral_code:
        return profile.referral_code

    code_length = int(global_config.referrals.code_length)
    for _ in range(_MAX_CODE_ATTEMPTS):
        code = _generate_referral_code(code_length)
        profile.referral_code = code
        db.add(profile)
        try:
            db.commit()
            db.refresh(profile)
            return code
        except IntegrityError:
            db.rollback()
            # Collision; try again.
            continue

    raise HTTPException(
        status_code=500, detail="Failed to generate a unique referral code"
    )


class ReferralMeResponse(BaseModel):
    referral_code: str
    referred_by_user_id: str | None
    referred_at: str | None
    referred_count: int


class ClaimReferralRequest(BaseModel):
    referral_code: str


@router.get("/referrals/me", response_model=ReferralMeResponse)
async def get_my_referral_info(
    request: Request,
    db: Session = Depends(get_db_session),
):
    user = await get_authenticated_user(request, db)
    user_uuid = user_uuid_from_str(user.id)

    profile = _ensure_profile_exists(db, user_uuid, user.email)
    referral_code = _ensure_referral_code(db, profile)

    referred_count = (
        db.query(Profiles).filter(Profiles.referred_by_user_id == user_uuid).count()
    )

    return ReferralMeResponse(
        referral_code=referral_code,
        referred_by_user_id=(
            str(profile.referred_by_user_id) if profile.referred_by_user_id else None
        ),
        referred_at=profile.referred_at.isoformat() if profile.referred_at else None,
        referred_count=referred_count,
    )


@router.post("/referrals/claim", response_model=ReferralMeResponse)
async def claim_referral(
    payload: ClaimReferralRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    user = await get_authenticated_user(request, db)
    user_uuid = user_uuid_from_str(user.id)

    profile = _ensure_profile_exists(db, user_uuid, user.email)
    if profile.referred_by_user_id is not None:
        raise HTTPException(status_code=409, detail="Referral already claimed")

    code = _normalize_referral_code(payload.referral_code)
    if not code:
        raise HTTPException(status_code=400, detail="Referral code is required")

    referrer = db.query(Profiles).filter(Profiles.referral_code == code).first()
    if not referrer:
        raise HTTPException(status_code=404, detail="Referral code not found")

    if str(referrer.user_id) == str(profile.user_id):
        raise HTTPException(status_code=400, detail="Cannot refer yourself")

    referee_award = int(global_config.referrals.credit_award.referee)
    referrer_award = int(global_config.referrals.credit_award.referrer)

    with db_transaction(db):
        profile.referred_by_user_id = referrer.user_id
        profile.referred_at = _utcnow()

        if referee_award:
            profile.credits = int(profile.credits or 0) + referee_award
        if referrer_award:
            referrer.credits = int(referrer.credits or 0) + referrer_award

        db.add(profile)
        db.add(referrer)

    referral_code = _ensure_referral_code(db, profile)
    referred_count = (
        db.query(Profiles).filter(Profiles.referred_by_user_id == user_uuid).count()
    )

    return ReferralMeResponse(
        referral_code=referral_code,
        referred_by_user_id=str(profile.referred_by_user_id),
        referred_at=profile.referred_at.isoformat() if profile.referred_at else None,
        referred_count=referred_count,
    )

