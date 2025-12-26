from sqlalchemy.orm import Session
from src.db.models.public.profiles import Profiles, generate_referral_code


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

        user_profile.referrer_id = referrer.user_id
        referrer.referral_count += 1
        db.add(user_profile)
        db.add(referrer)
        db.commit()
        db.refresh(user_profile)
        return True

    @staticmethod
    def get_or_create_referral_code(db: Session, profile: Profiles) -> str:
        """
        Get the referral code for a profile, generating one if it doesn't exist.
        """
        if profile.referral_code:
            return str(profile.referral_code)

        # Lazy generation
        code = generate_referral_code()
        # Retry logic for uniqueness
        retries = 0
        while db.query(Profiles).filter(Profiles.referral_code == code).first():
            code = generate_referral_code()
            retries += 1
            if retries > 5:
                # Fallback to longer code
                code = generate_referral_code(12)
                break

        profile.referral_code = code
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return str(code)
