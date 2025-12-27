from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles
from src.db.utils.db_transaction import db_transaction
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
    If not, create one.
    """
    profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()

    if not profile:
        logger.info(f"Creating new profile for user {user_uuid}")

        try:
            with db_transaction(db):
                profile = Profiles(
                    user_id=user_uuid,
                    email=email,
                    username=username,
                    avatar_url=avatar_url,
                    is_approved=is_approved
                )
                db.add(profile)
            db.refresh(profile)
        except HTTPException:
            # Race condition: profile may have been created by concurrent request
            profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()
            if not profile:
                raise

    return profile

    return profile
