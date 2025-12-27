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


class TestReferralUpgrade(TestTemplate):

    @pytest.fixture
    def db_session(self):
        session = create_db_session()
        yield session
        # Clean up code might be needed if transactions are not rolled back properly
        # But for now, we'll rely on unique data
        session.close()

    def test_referral_reward_grant(self, db_session: Session):
        """Test that a user gets 6 months of Plus Tier after 5 referrals."""

        # Unique referral code
        referral_code = f"REF_{uuid.uuid4().hex[:8]}"

        # 1. Create Referrer
        referrer_id = uuid.uuid4()
        referrer = Profiles(
            user_id=referrer_id,
            email=f"referrer_{referrer_id}@example.com",
            referral_code=referral_code,
            referral_count=0,
        )
        db_session.add(referrer)
        db_session.commit()

        # 2. Process 4 Referrals (Should not trigger reward)
        for i in range(4):
            referee_id = uuid.uuid4()
            referee = Profiles(
                user_id=referee_id, email=f"referee_{i}_{referee_id}@example.com"
            )
            db_session.add(referee)
            db_session.commit()

            success = ReferralService.apply_referral(db_session, referee, referral_code)
            assert success is True

        # Verify referrer count is 4
        db_session.refresh(referrer)
        assert referrer.referral_count == 4

        # Verify NO subscription yet (or at least not the reward)
        sub = (
            db_session.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == referrer_id)
            .first()
        )
        assert sub is None

        # 3. Process 5th Referral (Should trigger reward)
        referee_5_id = uuid.uuid4()
        referee_5 = Profiles(
            user_id=referee_5_id, email=f"referee_5_{referee_5_id}@example.com"
        )
        db_session.add(referee_5)
        db_session.commit()

        success = ReferralService.apply_referral(db_session, referee_5, referral_code)
        assert success is True

        # Verify referrer count is 5
        db_session.refresh(referrer)
        assert referrer.referral_count == 5

        # Verify Subscription Granted
        sub = (
            db_session.query(UserSubscriptions)
            .filter(UserSubscriptions.user_id == referrer_id)
            .first()
        )
        assert sub is not None
        assert sub.subscription_tier == SubscriptionTier.PLUS.value
        assert sub.is_active is True

        # Verify Duration (Approx 6 months)
        now = datetime.now(timezone.utc)
        expected_end_min = now + timedelta(days=30 * 6) - timedelta(minutes=5)
        expected_end_max = now + timedelta(days=30 * 6) + timedelta(minutes=5)

        sub_end = sub.subscription_end_date
        if sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)

        assert expected_end_min <= sub_end <= expected_end_max

    def test_referral_reward_extension(self, db_session: Session):
        """Test that existing subscription is extended."""

        # Unique referral code
        referral_code = f"REF_{uuid.uuid4().hex[:8]}"

        # 1. Create Referrer with existing subscription
        referrer_id = uuid.uuid4()
        referrer = Profiles(
            user_id=referrer_id,
            email=f"referrer_ext_{referrer_id}@example.com",
            referral_code=referral_code,
            referral_count=4,  # Start at 4 for convenience
        )
        db_session.add(referrer)

        # Existing subscription ending in 1 month
        now = datetime.now(timezone.utc)
        existing_end = now + timedelta(days=30)
        sub = UserSubscriptions(
            user_id=referrer_id,
            subscription_tier=SubscriptionTier.PLUS.value,
            is_active=True,
            subscription_end_date=existing_end,
        )
        db_session.add(sub)
        db_session.commit()

        # 2. Process 5th Referral
        referee_id = uuid.uuid4()
        referee = Profiles(
            user_id=referee_id, email=f"referee_ext_{referee_id}@example.com"
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

        # Should be existing end + 6 months
        expected_end_min = existing_end + timedelta(days=30 * 6) - timedelta(minutes=5)
        expected_end_max = existing_end + timedelta(days=30 * 6) + timedelta(minutes=5)

        assert expected_end_min <= sub_end <= expected_end_max
