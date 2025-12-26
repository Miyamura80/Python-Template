from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.db.models.public.profiles import Profiles, generate_referral_code
from src.db.utils.db_transaction import db_transaction


class ReferralService:
    @staticmethod
    def validate_referral_code(
        db: Session, referral_code: str | None
    ) -> Profiles | None:
        """
        Validate a referral code and return the referrer's profile.
        """
        if not referral_code:
            return None
        return (
            db.query(Profiles).filter(Profiles.referral_code == referral_code).first()
        )

    @staticmethod
    def apply_referral(db: Session, user_profile: Profiles, referral_code: str) -> bool:
        """
        Apply a referral code to a user profile.
        Returns True if successful, False otherwise.
        """
        if user_profile.referrer_id:
            # User already has a referrer
            return False

        referrer = ReferralService.validate_referral_code(db, referral_code)
        if not referrer:
            return False

        if referrer.user_id == user_profile.user_id:
            # Cannot refer yourself
            return False

        with db_transaction(db):
            user_profile.referrer_id = referrer.user_id
            referrer.referral_count += 1
            db.add(user_profile)
            db.add(referrer)

        db.refresh(user_profile)
        return True

    @staticmethod
    def get_or_create_referral_code(db: Session, profile: Profiles) -> str:
        """
        Get the referral code for a profile, generating one if it doesn't exist.
        """
        if profile.referral_code:
            return str(profile.referral_code)

        # Lazy generation with retry on collision
        for _ in range(5):
            try:
                code = generate_referral_code()
                # Use db_transaction to ensure atomic commit/rollback on error
                # Note: db_transaction handles commit on success and rollback on error
                # but we need to catch IntegrityError specifically for retry
                # So we might need nested try/except or rely on db_transaction re-raising

                # Simplified approach: Just try commit.
                # If we use db_transaction, it catches exceptions and rolls back, then re-raises 500.
                # But we want to catch IntegrityError specifically.
                # So maybe NOT use db_transaction here if we want custom retry logic?
                # Or use it and catch the HTTPException(500) it raises? That's messy.
                # I'll stick to manual commit here for the retry loop as it is specific control flow.

                profile.referral_code = code
                db.add(profile)
                db.commit()
                db.refresh(profile)
                return str(code)
            except IntegrityError:
                db.rollback()
                continue

        # Fallback to longer code if collision persists
        code = generate_referral_code(12)
        profile.referral_code = code
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return str(code)
