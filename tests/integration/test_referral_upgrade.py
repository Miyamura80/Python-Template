
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.api.services.referral_service import ReferralService
from src.db.models.public.profiles import Profiles
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.db.models.stripe.subscription_types import SubscriptionTier
from tests.test_template import TestTemplate
from src.db.database import create_db_session
from common.global_config import global_config

class TestReferralUpgrade(TestTemplate):

    @pytest.fixture
    @pytest.fixture
    def db_session(self):
        session = create_db_session()
        yield session
        # Clean up test data
        session.rollback()
        session.close()

    def test_referral_reward_grant(self, db_session: Session):
        """Test that a user gets Plus Tier after required referrals."""

        # Get config values
        required_referrals = global_config.subscription.referral.referrals_required
        reward_months = global_config.subscription.referral.reward_months

        # Unique referral code
        referral_code = f"REF_{uuid.uuid4().hex[:8]}"

        # 1. Create Referrer
        referrer_id = uuid.uuid4()
        referrer = Profiles(
            user_id=referrer_id,
            email=f"referrer_{referrer_id}@example.com",
            referral_code=referral_code,
            referral_count=0
        )
        db_session.add(referrer)
        db_session.commit()

        # 2. Process N-1 Referrals (Should not trigger reward)
        for i in range(required_referrals - 1):
            referee_id = uuid.uuid4()
            referee = Profiles(
                user_id=referee_id,
                email=f"referee_{i}_{referee_id}@example.com"
            )
            db_session.add(referee)
            db_session.commit()

            success = ReferralService.apply_referral(db_session, referee, referral_code)
            assert success is True

        # Verify referrer count is N-1
        db_session.refresh(referrer)
        assert referrer.referral_count == required_referrals - 1

        # Verify NO subscription yet (or at least not the reward)
        sub = db_session.query(UserSubscriptions).filter(UserSubscriptions.user_id == referrer_id).first()
        assert sub is None

        # 3. Process Nth Referral (Should trigger reward)
        referee_final_id = uuid.uuid4()
        referee_final = Profiles(
            user_id=referee_final_id,
            email=f"referee_final_{referee_final_id}@example.com"
        )
        db_session.add(referee_final)
        db_session.commit()

        success = ReferralService.apply_referral(db_session, referee_final, referral_code)
        assert success is True

        # Verify referrer count is N
        db_session.refresh(referrer)
        assert referrer.referral_count == required_referrals

        # Verify Subscription Granted
        sub = db_session.query(UserSubscriptions).filter(UserSubscriptions.user_id == referrer_id).first()
        assert sub is not None
        assert sub.subscription_tier == SubscriptionTier.PLUS.value
        assert sub.is_active is True

        # Verify Duration (Approx reward_months)
        now = datetime.now(timezone.utc)
        expected_duration = timedelta(days=30 * reward_months)
        expected_end_min = now + expected_duration - timedelta(minutes=5)
        expected_end_max = now + expected_duration + timedelta(minutes=5)

        sub_end = sub.subscription_end_date
        if sub_end.tzinfo is None:
             sub_end = sub_end.replace(tzinfo=timezone.utc)

        assert expected_end_min <= sub_end <= expected_end_max

    def test_referral_reward_extension(self, db_session: Session):
        """Test that existing subscription is extended."""

        # Get config values
        required_referrals = global_config.subscription.referral.referrals_required
        reward_months = global_config.subscription.referral.reward_months

        # Unique referral code
        referral_code = f"REF_{uuid.uuid4().hex[:8]}"

        # 1. Create Referrer with existing subscription
        referrer_id = uuid.uuid4()
        referrer = Profiles(
            user_id=referrer_id,
            email=f"referrer_ext_{referrer_id}@example.com",
            referral_code=referral_code,
            referral_count=required_referrals - 1 # Start just before threshold
        )
        db_session.add(referrer)

        # Existing subscription ending in 1 month
        now = datetime.now(timezone.utc)
        existing_end = now + timedelta(days=30)
        sub = UserSubscriptions(
            user_id=referrer_id,
            subscription_tier=SubscriptionTier.PLUS.value,
            is_active=True,
            subscription_end_date=existing_end
        )
        db_session.add(sub)
        db_session.commit()

        # 2. Process Final Referral
        referee_id = uuid.uuid4()
        referee = Profiles(
            user_id=referee_id,
            email=f"referee_ext_{referee_id}@example.com"
        )
        db_session.add(referee)
        db_session.commit()

        success = ReferralService.apply_referral(db_session, referee, referral_code)
        assert success is True

        # Verify Extension
        db_session.refresh(sub)
        sub_end = sub.subscription_end_date
        if sub_end.tzinfo is None:
             sub_end = sub_end.replace(tzinfo=timezone.utc)

        # Should be existing end + reward_months
        reward_duration = timedelta(days=30 * reward_months)
        expected_end_min = existing_end + reward_duration - timedelta(minutes=5)
        expected_end_max = existing_end + reward_duration + timedelta(minutes=5)

        assert expected_end_min <= sub_end <= expected_end_max
