from src.db.models.public.profiles import Profiles
from src.db.utils.users import ensure_profile_exists
import uuid

def test_ensure_profile_exists_no_code_generated_by_default(db_session):
    user_id = uuid.uuid4()
    email = "test@example.com"

    # Ensure profile doesn't exist
    assert db_session.query(Profiles).filter_by(user_id=user_id).first() is None

    # Create profile
    profile = ensure_profile_exists(db_session, user_id, email)

    # Verify code was NOT generated (since we removed default generation in models)
    assert profile is not None
    assert profile.referral_code is None

    # Verify persistence
    fetched_profile = db_session.query(Profiles).filter_by(user_id=user_id).first()
    assert fetched_profile.referral_code is None

def test_ensure_profile_exists_respects_is_approved(db_session):
    user_id = uuid.uuid4()
    email = "approved@example.com"

    profile = ensure_profile_exists(db_session, user_id, email, is_approved=True)
    assert profile.is_approved is True

    fetched = db_session.query(Profiles).filter_by(user_id=user_id).first()
    assert fetched.is_approved is True
