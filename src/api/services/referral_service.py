from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles

class ReferralService:
    @staticmethod
    def validate_referral_code(db: Session, referral_code: str) -> Profiles | None:
        """
        Validate a referral code and return the referrer's profile.
        """
        return db.query(Profiles).filter(Profiles.referral_code == referral_code).first()

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

        user_profile.referrer_id = referrer.user_id
        referrer.referral_count += 1
        db.add(user_profile)
        db.add(referrer)
        db.commit()
        db.refresh(user_profile)
        return True
