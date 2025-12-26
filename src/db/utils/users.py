from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles, generate_referral_code
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
    If not, create one with a generated referral code.
    """
    profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()

    if not profile:
        logger.info(f"Creating new profile for user {user_uuid}")

        # Generate a unique referral code
        referral_code = generate_referral_code()
        # Simple retry logic for collision (though unlikely with 8 chars)
        retries = 0
        while db.query(Profiles).filter(Profiles.referral_code == referral_code).first():
            referral_code = generate_referral_code()
            retries += 1
            if retries > 5:
                logger.error("Failed to generate unique referral code after 5 attempts")
                # Fallback to UUID-based or longer code if this happens
                referral_code = generate_referral_code(12)
                break

        profile = Profiles(
            user_id=user_uuid,
            email=email,
            username=username,
            avatar_url=avatar_url,
            referral_code=referral_code,
            is_approved=is_approved
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile
