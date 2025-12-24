"""
E2E tests for referral endpoints
"""

import pytest
import jwt
import time
import uuid
from datetime import datetime

from tests.e2e.e2e_test_base import E2ETestBase
from common import global_config
from src.db.models.public.referrals import Referral
from src.db.models.public.profiles import Profiles


class TestReferrals(E2ETestBase):
    """Tests for the referral endpoints"""

    @pytest.fixture(autouse=True)
    def setup_referral_test(self, db):
        """Clean up any existing referrals before each test"""
        # Clean up referrals for the test user
        if hasattr(self, "user_id"):
            db.query(Referral).filter(
                (Referral.referrer_user_id == self.user_id)
                | (Referral.referred_user_id == self.user_id)
            ).delete(synchronize_session=False)
            db.commit()
        yield
        # Clean up after test
        if hasattr(self, "user_id"):
            db.query(Referral).filter(
                (Referral.referrer_user_id == self.user_id)
                | (Referral.referred_user_id == self.user_id)
            ).delete(synchronize_session=False)
            db.commit()

    def test_create_referral_code(self, db):
        """Test creating a new referral code"""
        response = self.client.post("/referrals/code", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "referral_code" in data
        assert "created_at" in data

        # Verify referral code format
        assert len(data["referral_code"]) == global_config.referral.code_length

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data["created_at"])
        except ValueError:
            pytest.fail(f"Timestamp '{data['created_at']}' is not valid ISO format")

    def test_create_referral_code_returns_existing(self, db):
        """Test that creating a referral code when one exists returns the existing one"""
        # First request creates a new code
        response1 = self.client.post("/referrals/code", headers=self.auth_headers)
        assert response1.status_code == 200
        code1 = response1.json()["referral_code"]

        # Second request should return the same code
        response2 = self.client.post("/referrals/code", headers=self.auth_headers)
        assert response2.status_code == 200
        code2 = response2.json()["referral_code"]

        assert code1 == code2

    def test_get_referral_code(self, db):
        """Test getting an existing referral code"""
        # First create a code
        create_response = self.client.post("/referrals/code", headers=self.auth_headers)
        assert create_response.status_code == 200
        created_code = create_response.json()["referral_code"]

        # Then get the code
        get_response = self.client.get("/referrals/code", headers=self.auth_headers)
        assert get_response.status_code == 200
        retrieved_code = get_response.json()["referral_code"]

        assert created_code == retrieved_code

    def test_get_referral_code_not_found(self, db):
        """Test getting referral code when none exists returns 404"""
        # Clean up any existing referrals for this user first
        db.query(Referral).filter(Referral.referrer_user_id == self.user_id).delete(
            synchronize_session=False
        )
        db.commit()

        response = self.client.get("/referrals/code", headers=self.auth_headers)
        assert response.status_code == 404

    def test_get_referral_stats(self, db):
        """Test getting referral statistics"""
        # First create a code
        self.client.post("/referrals/code", headers=self.auth_headers)

        response = self.client.get("/referrals/stats", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_referrals" in data
        assert "completed_referrals" in data
        assert "pending_referrals" in data
        assert "total_credits_earned" in data
        assert "referral_code" in data

        # Initially, no completed referrals
        assert data["total_referrals"] == 0
        assert data["completed_referrals"] == 0
        assert data["pending_referrals"] == 1  # The code we just created

    def test_list_referrals_empty(self, db):
        """Test listing referrals when none exist"""
        response = self.client.get("/referrals/list", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "referrals" in data
        assert "total_count" in data
        assert data["total_count"] == 0
        assert len(data["referrals"]) == 0

    def test_apply_referral_code_invalid(self, db):
        """Test applying an invalid referral code returns 404"""
        response = self.client.post(
            "/referrals/apply",
            headers=self.auth_headers,
            json={"referral_code": "INVALID123"},
        )

        assert response.status_code == 404
        assert "Invalid or expired referral code" in response.json()["detail"]

    def test_apply_own_referral_code_fails(self, db):
        """Test that a user cannot apply their own referral code"""
        # First create a code
        create_response = self.client.post("/referrals/code", headers=self.auth_headers)
        assert create_response.status_code == 200
        code = create_response.json()["referral_code"]

        # Try to apply own code
        response = self.client.post(
            "/referrals/apply",
            headers=self.auth_headers,
            json={"referral_code": code},
        )

        assert response.status_code == 400
        assert "cannot use your own referral code" in response.json()["detail"]

    def test_referral_endpoints_require_auth(self):
        """Test that referral endpoints require authentication"""
        # Test all endpoints without auth
        endpoints = [
            ("POST", "/referrals/code"),
            ("GET", "/referrals/code"),
            ("POST", "/referrals/apply"),
            ("GET", "/referrals/stats"),
            ("GET", "/referrals/list"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            else:
                response = self.client.post(endpoint, json={})

            assert (
                response.status_code == 401
            ), f"Expected 401 for {method} {endpoint}, got {response.status_code}"


class TestReferralApply(E2ETestBase):
    """Tests for the referral apply flow with multiple users"""

    def _create_test_user_headers(self, user_suffix: str, db):
        """Create auth headers for a test user"""
        test_email = f"test_user_{user_suffix}@test.com"
        test_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test_user_{user_suffix}"))

        # Create JWT token
        token_payload = {
            "sub": test_user_id,
            "email": test_email,
            "first_name": "Test",
            "last_name": f"User{user_suffix}",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "https://api.workos.com",
            "aud": global_config.WORKOS_CLIENT_ID,
        }

        token = jwt.encode(token_payload, "test-secret", algorithm="HS256")

        # Ensure profile exists
        profile = db.query(Profiles).filter(Profiles.user_id == test_user_id).first()
        if not profile:
            profile = Profiles(
                user_id=test_user_id,
                email=test_email,
                is_approved=True,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        return {"Authorization": f"Bearer {token}"}, test_user_id

    @pytest.fixture(autouse=True)
    def setup_multi_user_test(self, db):
        """Set up test users for referral apply tests"""
        self.referrer_headers, self.referrer_id = self._create_test_user_headers(
            "referrer", db
        )
        self.referred_headers, self.referred_id = self._create_test_user_headers(
            "referred", db
        )

        # Clean up any existing referrals
        db.query(Referral).filter(
            (Referral.referrer_user_id == self.referrer_id)
            | (Referral.referred_user_id == self.referred_id)
        ).delete(synchronize_session=False)
        db.commit()

        yield

        # Clean up after test
        db.query(Referral).filter(
            (Referral.referrer_user_id == self.referrer_id)
            | (Referral.referred_user_id == self.referred_id)
        ).delete(synchronize_session=False)
        db.commit()

    def test_apply_referral_code_success(self, db):
        """Test successfully applying a referral code"""
        # Referrer creates a code
        create_response = self.client.post(
            "/referrals/code", headers=self.referrer_headers
        )
        assert create_response.status_code == 200
        code = create_response.json()["referral_code"]

        # Referred user applies the code
        apply_response = self.client.post(
            "/referrals/apply",
            headers=self.referred_headers,
            json={"referral_code": code},
        )

        assert apply_response.status_code == 200
        data = apply_response.json()

        assert data["success"] is True
        assert data["credits_awarded"] == global_config.referral.credits_for_referred
        assert "credits" in data["message"].lower()

    def test_apply_referral_code_twice_fails(self, db):
        """Test that a user cannot apply a referral code twice"""
        # Referrer creates a code
        create_response = self.client.post(
            "/referrals/code", headers=self.referrer_headers
        )
        assert create_response.status_code == 200
        code = create_response.json()["referral_code"]

        # Referred user applies the code first time
        first_apply = self.client.post(
            "/referrals/apply",
            headers=self.referred_headers,
            json={"referral_code": code},
        )
        assert first_apply.status_code == 200

        # Referrer creates another code (since the first one is now used)
        create_response2 = self.client.post(
            "/referrals/code", headers=self.referrer_headers
        )
        assert create_response2.status_code == 200
        code2 = create_response2.json()["referral_code"]

        # Referred user tries to apply another code
        second_apply = self.client.post(
            "/referrals/apply",
            headers=self.referred_headers,
            json={"referral_code": code2},
        )

        assert second_apply.status_code == 400
        assert "already used a referral code" in second_apply.json()["detail"]

    def test_referral_awards_credits_to_both_users(self, db):
        """Test that completing a referral awards credits to both users"""
        # Get initial credits for both users
        referrer_profile = (
            db.query(Profiles).filter(Profiles.user_id == self.referrer_id).first()
        )
        referred_profile = (
            db.query(Profiles).filter(Profiles.user_id == self.referred_id).first()
        )

        initial_referrer_credits = referrer_profile.credits or 0
        initial_referred_credits = referred_profile.credits or 0

        # Referrer creates a code
        create_response = self.client.post(
            "/referrals/code", headers=self.referrer_headers
        )
        code = create_response.json()["referral_code"]

        # Referred user applies the code
        self.client.post(
            "/referrals/apply",
            headers=self.referred_headers,
            json={"referral_code": code},
        )

        # Refresh profiles from database
        db.refresh(referrer_profile)
        db.refresh(referred_profile)

        # Verify credits were awarded
        assert referrer_profile.credits == (
            initial_referrer_credits + global_config.referral.credits_for_referrer
        )
        assert referred_profile.credits == (
            initial_referred_credits + global_config.referral.credits_for_referred
        )

    def test_referral_updates_referrer_stats(self, db):
        """Test that completing a referral updates the referrer's stats"""
        # Referrer creates a code
        create_response = self.client.post(
            "/referrals/code", headers=self.referrer_headers
        )
        code = create_response.json()["referral_code"]

        # Check initial stats
        initial_stats = self.client.get(
            "/referrals/stats", headers=self.referrer_headers
        ).json()
        assert initial_stats["completed_referrals"] == 0

        # Referred user applies the code
        self.client.post(
            "/referrals/apply",
            headers=self.referred_headers,
            json={"referral_code": code},
        )

        # Check updated stats
        updated_stats = self.client.get(
            "/referrals/stats", headers=self.referrer_headers
        ).json()
        assert updated_stats["completed_referrals"] == 1
        assert (
            updated_stats["total_credits_earned"]
            == global_config.referral.credits_for_referrer
        )
