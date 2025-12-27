from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.db.models.public.profiles import Profiles, generate_referral_code
from src.db.utils.db_transaction import db_transaction
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.db.models.stripe.subscription_types import SubscriptionTier
from datetime import datetime, timedelta, timezone
from loguru import logger
from typing import cast
import uuid


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
    def grant_referral_reward(db: Session, user_id: uuid.UUID):
        """
        Grant 6 months of Plus Tier to the user.
        """
        now = datetime.now(timezone.utc)
        six_months = timedelta(days=30 * 6)

        subscription = (
            db.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == user_id)
            .first()
        )

        if subscription:
            subscription.subscription_tier = SubscriptionTier.PLUS.value
            subscription.is_active = True

            # If current subscription is valid and ends in the future, extend it
            # Otherwise start from now
            current_end = subscription.subscription_end_date
            if current_end and current_end.tzinfo is None:
                # Assuming UTC if naive, though model says TIMESTAMP which is usually naive in SQLA unless timezone=True
                # But profiles.py uses DateTime(timezone=True). UserSubscriptions uses TIMESTAMP.
                # Postgres TIMESTAMP without time zone vs with time zone.
                # Let's assume naive means UTC or handle it carefully.
                # Actually, `datetime.now(timezone.utc)` returns aware.
                # If DB returns naive, we should probably treat it as UTC.
                current_end = current_end.replace(tzinfo=timezone.utc)

            if current_end and current_end > now:
                subscription.subscription_end_date = current_end + six_months
            else:
                subscription.subscription_end_date = now + six_months

            logger.info(f"Updated subscription for user {user_id} via referral reward")
        else:
            new_subscription = UserSubscriptions(
                user_id=user_id,
                subscription_tier=SubscriptionTier.PLUS.value,
                is_active=True,
                subscription_start_date=now,
                subscription_end_date=now + six_months,
            )
            db.add(new_subscription)
            logger.info(f"Created subscription for user {user_id} via referral reward")

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

            # Refresh referrer to get updated count and trigger reward if applicable
            db.refresh(referrer)

            if referrer.referral_count == 5:
                # Cast user_id to uuid.UUID to satisfy ty type checker
                # SQLAlchemy models sometimes return Column types in static analysis
                user_id = cast(uuid.UUID, referrer.user_id)
                ReferralService.grant_referral_reward(db, user_id)

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
