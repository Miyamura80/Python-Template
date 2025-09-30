import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest_asyncio
import jwt

import ssl

from src.api.auth.jwt_utils import decode_jwt_payload, extract_bearer_token

from src.server import app
from src.db.database import get_db_session
from tests.test_template import TestTemplate
from common import global_config
from src.utils.logging_config import setup_logging
from src.db.models.public.profiles import WaitlistStatus, Profiles


setup_logging(debug=True)


class E2ETestBase(TestTemplate):
    """Base class for E2E tests with common fixtures and utilities"""

    @pytest.fixture(autouse=True)
    def setup_test(self, setup):
        """Setup test client"""
        self.client = TestClient(app)
        self.test_user_id = None  # Initialize user ID

    @pytest_asyncio.fixture
    async def db(self) -> Session:
        """Get database session"""
        db = next(get_db_session())
        try:
            yield db
        finally:
            db.close()

    @pytest_asyncio.fixture
    async def auth_headers(self, db: Session):
        """Get authentication token for test user and approve them"""
        ssl_context = ssl.create_default_context()
        async with httpx.AsyncClient(verify=ssl_context) as client:
            response = await client.post(
                f"{global_config.SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": global_config.SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "email": global_config.TEST_USER_EMAIL,
                    "password": global_config.TEST_USER_PASSWORD,
                },
            )

            assert response.status_code == 200
            token = response.json()["access_token"]

            # Extract user ID from token and store it
            user_info = self.get_user_from_token(token)
            self.test_user_id = user_info["id"]
            self.test_user_email = user_info["email"]

            # Ensure the user profile exists and is approved for tests
            profile = db.query(Profiles).filter(Profiles.user_id == self.test_user_id).first()
            if not profile:
                profile = Profiles(
                    user_id=self.test_user_id,
                    email=self.test_user_email,
                    is_approved=True,
                    waitlist_status=WaitlistStatus.APPROVED
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)
            elif not profile.is_approved:
                profile.is_approved = True
                profile.waitlist_status = WaitlistStatus.APPROVED
                db.commit()
                db.refresh(profile)

            return {"Authorization": f"Bearer {token}"}

    def get_user_from_token(self, token):
        """Helper method to get user info from auth token by decoding JWT directly"""
        try:
            decoded = decode_jwt_payload(token)
            user_info = {
                "id": decoded["sub"],
                "email": decoded["email"],
                "app_metadata": decoded.get("app_metadata", {}),
                "user_metadata": decoded.get("user_metadata", {}),
            }
            return user_info
        except Exception as e:
            print(f"Error decoding JWT: {str(e)}")
            raise ValueError(f"Failed to extract user info from token: {str(e)}")

    def get_user_from_auth_headers(self, auth_headers):
        """Helper method to extract user info from auth headers"""
        token = extract_bearer_token(auth_headers.get("Authorization"))
        return self.get_user_from_token(token)

    def decode_jwt_token(self, token, verify=False):
        """Helper method to decode JWT token

        Args:
            token (str): JWT token to decode
            verify (bool): Whether to verify the token signature

        Returns:
            dict: Decoded token payload
        """
        return jwt.decode(token, options={"verify_signature": not verify})
