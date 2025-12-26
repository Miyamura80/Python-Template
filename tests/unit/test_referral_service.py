from src.api.services.referral_service import ReferralService
from src.db.models.public.profiles import Profiles, generate_referral_code
import uuid

def test_apply_referral_success(db_session):
    # Create referrer
    referrer_id = uuid.uuid4()
    referrer_code = generate_referral_code()
    referrer = Profiles(user_id=referrer_id, email="referrer@example.com", referral_code=referrer_code)
    db_session.add(referrer)

    # Create user
    user_id = uuid.uuid4()
    user_code = generate_referral_code()
    user = Profiles(user_id=user_id, email="user@example.com", referral_code=user_code)
    db_session.add(user)
    db_session.commit()

    # Apply referral
    result = ReferralService.apply_referral(db_session, user, referrer_code)

    assert result is True

    # Verify updates
    db_session.refresh(user)
    db_session.refresh(referrer)

    assert user.referrer_id == referrer_id
    assert referrer.referral_count == 1

def test_apply_referral_self_referral_fails(db_session):
    user_id = uuid.uuid4()
    user_code = generate_referral_code()
    user = Profiles(user_id=user_id, email="self@example.com", referral_code=user_code)
    db_session.add(user)
    db_session.commit()

    result = ReferralService.apply_referral(db_session, user, user_code)

    assert result is False
    assert user.referrer_id is None

def test_apply_referral_already_referred_fails(db_session):
    # Create referrer
    referrer_id = uuid.uuid4()
    referrer_code = generate_referral_code()
    referrer = Profiles(user_id=referrer_id, referral_code=referrer_code)
    db_session.add(referrer)

    # Create user already referred
    user_id = uuid.uuid4()
    user_code = generate_referral_code()
    user = Profiles(user_id=user_id, referral_code=user_code, referrer_id=referrer_id)
    db_session.add(user)
    db_session.commit()

    # Try to refer again with different referrer
    other_referrer_code = generate_referral_code()
    other_referrer = Profiles(user_id=uuid.uuid4(), referral_code=other_referrer_code)
    db_session.add(other_referrer)
    db_session.commit()

    result = ReferralService.apply_referral(db_session, user, other_referrer_code)

    assert result is False
    assert user.referrer_id == referrer_id

def test_apply_referral_invalid_code_fails(db_session):
    user_id = uuid.uuid4()
    user_code = generate_referral_code()
    user = Profiles(user_id=user_id, referral_code=user_code)
    db_session.add(user)
    db_session.commit()

    result = ReferralService.apply_referral(db_session, user, "INVALIDCODE")

    assert result is False
    assert user.referrer_id is None
