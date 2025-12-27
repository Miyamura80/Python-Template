from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.db.models.public.profiles import Profiles, generate_referral_code
from src.db.utils.db_transaction import db_transaction
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.db.models.stripe.subscription_types import SubscriptionTier
from common.global_config import global_config
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
        Grant Plus Tier to the user based on configured reward duration.
        """
        now = datetime.now(timezone.utc)
        reward_months = global_config.subscription.referral.reward_months
        reward_duration = timedelta(days=30 * reward_months)

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
                current_end = current_end.replace(tzinfo=timezone.utc)

            if current_end and current_end > now:
                subscription.subscription_end_date = current_end + reward_duration
            else:
                subscription.subscription_end_date = now + reward_duration

            logger.info(
                f"Updated subscription for user {user_id} via referral reward ({reward_months} months)"
            )
        else:
            new_subscription = UserSubscriptions(
                user_id=user_id,
                subscription_tier=SubscriptionTier.PLUS.value,
                is_active=True,
                subscription_start_date=now,
                subscription_end_date=now + reward_duration,
            )
            db.add(new_subscription)
            logger.info(
                f"Created subscription for user {user_id} via referral reward ({reward_months} months)"
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

            # Refresh referrer to get updated count and trigger reward if applicable
            db.refresh(referrer)

            required_referrals = global_config.subscription.referral.referrals_required
            if referrer.referral_count == required_referrals:
                # Cast user_id to uuid.UUID to satisfy ty
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
