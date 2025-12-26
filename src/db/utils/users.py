from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles
import uuid
from loguru import logger

def ensure_profile_exists(
    db: Session,
    user_uuid: uuid.UUID,
    email: str | None = None,
    username: str | None = None,
    avatar_url: str | None = None,
    is_approved: bool = False
) -> Profiles:
    """
    Ensure a profile exists for the given user UUID.
    If not, create one. Referral code is generated automatically by the model default.
    """
    profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()

    if not profile:
        logger.info(f"Creating new profile for user {user_uuid}")

        profile = Profiles(
            user_id=user_uuid,
            email=email,
            username=username,
            avatar_url=avatar_url,
            is_approved=is_approved
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile
