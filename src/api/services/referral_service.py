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

            # Atomic update to avoid race conditions
            db.query(Profiles).filter(Profiles.user_id == referrer.user_id).update(
                {Profiles.referral_count: Profiles.referral_count + 1}
            )

            db.add(user_profile)

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
