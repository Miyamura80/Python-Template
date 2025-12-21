"""
E2E tests for referral endpoints.
"""

import time
import uuid

import jwt

from common import global_config
from src.api.auth.utils import user_uuid_from_str
from tests.e2e.e2e_test_base import E2ETestBase


def _make_workos_headers(user_seed: str, email: str) -> tuple[str, dict[str, str]]:
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_seed))
    token_payload = {
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://api.workos.com",
        "aud": global_config.WORKOS_CLIENT_ID,
    }
    token = jwt.encode(token_payload, "test-secret", algorithm="HS256")
    return user_id, {"Authorization": f"Bearer {token}"}


class TestReferrals(E2ETestBase):
    def test_referrals_me_generates_code(self):
        user_id, headers = _make_workos_headers(
            user_seed=f"referrals_me_{uuid.uuid4().hex}",
            email="referrals_me@example.com",
        )
        response = self.client.get("/referrals/me", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["referral_code"]
        assert len(data["referral_code"]) == global_config.referrals.code_length
        assert data["referred_by_user_id"] is None
        assert data["referred_at"] is None
        assert isinstance(data["referred_count"], int)

        # Ensure the code is stable for the same user
        response2 = self.client.get("/referrals/me", headers=headers)
        assert response2.status_code == 200
        assert response2.json()["referral_code"] == data["referral_code"]

        # The authenticated id is still the WorkOS sub; the DB stores UUIDs derived from it.
        assert str(user_uuid_from_str(user_id))

    def test_referral_claim_sets_referred_by(self):
        referrer_id, referrer_headers = _make_workos_headers(
            user_seed=f"referrer_{uuid.uuid4().hex}",
            email="referrer@example.com",
        )
        referee_id, referee_headers = _make_workos_headers(
            user_seed=f"referee_{uuid.uuid4().hex}",
            email="referee@example.com",
        )

        # Referrer gets a referral code
        referrer_me = self.client.get("/referrals/me", headers=referrer_headers)
        assert referrer_me.status_code == 200
        referral_code = referrer_me.json()["referral_code"]
        assert referral_code

        # Referee claims it
        claim = self.client.post(
            "/referrals/claim",
            json={"referral_code": referral_code},
            headers=referee_headers,
        )
        assert claim.status_code == 200
        claim_data = claim.json()

        expected_referrer_uuid = str(user_uuid_from_str(referrer_id))
        assert claim_data["referred_by_user_id"] == expected_referrer_uuid
        assert claim_data["referred_at"] is not None

        # Referrer sees at least one referred user
        referrer_me_after = self.client.get("/referrals/me", headers=referrer_headers)
        assert referrer_me_after.status_code == 200
        assert referrer_me_after.json()["referred_count"] >= 1

        # Referee sees referred_by populated
        referee_me = self.client.get("/referrals/me", headers=referee_headers)
        assert referee_me.status_code == 200
        assert referee_me.json()["referred_by_user_id"] == expected_referrer_uuid

        # Ensure referee id was a valid UUID string
        assert str(user_uuid_from_str(referee_id))

    def test_referral_cannot_self_refer(self):
        user_id, headers = _make_workos_headers(
            user_seed=f"self_refer_{uuid.uuid4().hex}",
            email="self_refer@example.com",
        )
        me = self.client.get("/referrals/me", headers=headers)
        assert me.status_code == 200
        code = me.json()["referral_code"]

        claim = self.client.post(
            "/referrals/claim",
            json={"referral_code": code},
            headers=headers,
        )
        assert claim.status_code == 400
        assert "Cannot refer yourself" in claim.json()["detail"]

        assert str(user_uuid_from_str(user_id))

    def test_referral_cannot_claim_twice(self):
        referrer_id, referrer_headers = _make_workos_headers(
            user_seed=f"referrer_twice_{uuid.uuid4().hex}",
            email="referrer_twice@example.com",
        )
        referee_id, referee_headers = _make_workos_headers(
            user_seed=f"referee_twice_{uuid.uuid4().hex}",
            email="referee_twice@example.com",
        )

        referrer_me = self.client.get("/referrals/me", headers=referrer_headers)
        assert referrer_me.status_code == 200
        referral_code = referrer_me.json()["referral_code"]

        first_claim = self.client.post(
            "/referrals/claim",
            json={"referral_code": referral_code},
            headers=referee_headers,
        )
        assert first_claim.status_code == 200
        assert first_claim.json()["referred_by_user_id"] == str(
            user_uuid_from_str(referrer_id)
        )

        second_claim = self.client.post(
            "/referrals/claim",
            json={"referral_code": referral_code},
            headers=referee_headers,
        )
        assert second_claim.status_code == 409
        assert "Referral already claimed" in second_claim.json()["detail"]

        assert str(user_uuid_from_str(referee_id))

