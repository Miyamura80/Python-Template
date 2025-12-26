from src.api.services.referral_service import ReferralService
from src.db.models.public.profiles import Profiles
import uuid

def test_get_or_create_referral_code_lazy_generation(db_session):
    user_id = uuid.uuid4()
    profile = Profiles(user_id=user_id, email="lazy@example.com")
    db_session.add(profile)
    db_session.commit()

    assert profile.referral_code is None

    code = ReferralService.get_or_create_referral_code(db_session, profile)

    assert code is not None
    assert len(code) >= 8
    assert profile.referral_code == code

    # Call again should return same code
    code2 = ReferralService.get_or_create_referral_code(db_session, profile)
    assert code2 == code

def test_validate_referral_code_with_none(db_session):
    result = ReferralService.validate_referral_code(db_session, None)
    assert result is None

    result = ReferralService.validate_referral_code(db_session, "")
    assert result is None
