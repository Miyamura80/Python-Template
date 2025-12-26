from src.db.models.public.profiles import Profiles, generate_referral_code
from src.db.utils.users import ensure_profile_exists
import uuid

def test_generate_referral_code():
    code = generate_referral_code(8)
    assert len(code) == 8
    assert code.isalnum()
    assert code.isupper()

def test_ensure_profile_exists_creates_profile_with_referral_code(db_session):
    user_id = uuid.uuid4()
    email = "test@example.com"

    # Ensure profile doesn't exist
    assert db_session.query(Profiles).filter_by(user_id=user_id).first() is None

    # Create profile
    profile = ensure_profile_exists(db_session, user_id, email)

    assert profile is not None
    assert profile.user_id == user_id
    assert profile.email == email
    # referral_code is None by default now
    assert profile.referral_code is None

    # Ensure it's persisted
    fetched_profile = db_session.query(Profiles).filter_by(user_id=user_id).first()
    assert fetched_profile is not None
    assert fetched_profile.referral_code is None

def test_ensure_profile_exists_returns_existing(db_session):
    user_id = uuid.uuid4()
    email = "existing@example.com"

    # Manually create profile
    referral_code = generate_referral_code()
    profile = Profiles(user_id=user_id, email=email, referral_code=referral_code)
    db_session.add(profile)
    db_session.commit()

    # Call ensure_profile_exists
    retrieved_profile = ensure_profile_exists(db_session, user_id, email)

    assert retrieved_profile.user_id == profile.user_id
    assert retrieved_profile.referral_code == referral_code
