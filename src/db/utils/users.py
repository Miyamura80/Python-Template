from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles
from src.db.utils.db_transaction import db_transaction
import uuid
from src.utils.logging_config import setup_logging
from loguru import logger as log

setup_logging()

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
        log.info(f"Creating new profile for user {user_uuid}")

        with db_transaction(db):
            profile = Profiles(
                user_id=user_uuid,
                email=email,
                username=username,
                avatar_url=avatar_url,
                is_approved=is_approved
            )
            db.add(profile)
        # No need for explicit commit/refresh as db_transaction handles commit,
        # but we might need refresh if we access attributes immediately after.
        # db_transaction usually commits.
        db.refresh(profile)

    return profile
