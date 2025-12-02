import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest_asyncio
import jwt
import time
import uuid

from src.server import app
from src.db.database import get_db_session
from tests.test_template import TestTemplate
from common import global_config
from src.utils.logging_config import setup_logging
from src.db.models.public.profiles import WaitlistStatus, Profiles


setup_logging(debug=True)


class E2ETestBase(TestTemplate):
    """Base class for E2E tests with common fixtures and utilities using WorkOS authentication"""

    @pytest.fixture(autouse=True)
    def setup_test(self, setup):  # noqa
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
        """
        Get authentication token for test user and approve them.

        Creates a mock WorkOS JWT token for testing purposes.
        In production, this would come from actual WorkOS authentication.
        """
        # Use test user credentials from config
        test_user_email = global_config.TEST_USER_EMAIL
        # Use a consistent UUID for testing (deterministic UUID based on namespace)
        test_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "test_user_workos_001")

        # Create a mock WorkOS JWT token
        token_payload = {
            "sub": str(test_user_id),  # Subject (user ID)
            "email": test_user_email,
            "first_name": "Test",
            "last_name": "User",
            "iat": int(time.time()),  # Issued at
            "exp": int(time.time()) + 3600,  # Expires in 1 hour
            "iss": "https://api.workos.com",  # Issuer
            "aud": global_config.WORKOS_CLIENT_ID,  # Audience
        }

        # Create JWT token (unsigned for testing)
        token = jwt.encode(token_payload, "test-secret", algorithm="HS256")

        # Store user info for tests
        self.test_user_id = test_user_id
        self.test_user_email = test_user_email

        # Ensure the user profile exists and is approved for tests
        profile = (
            db.query(Profiles).filter(Profiles.user_id == self.test_user_id).first()
        )
        if not profile:
            profile = Profiles(
                user_id=self.test_user_id,
                email=self.test_user_email,
                is_approved=True,
                waitlist_status=WaitlistStatus.APPROVED,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        elif not profile.is_approved:
            profile.is_approved = True
            profile.waitlist_status = WaitlistStatus.APPROVED  # noqa
            db.commit()
            db.refresh(profile)

        return {"Authorization": f"Bearer {token}"}

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_user(self, db, auth_headers):
        """
        Set up test user with auth headers for authenticated E2E tests.

        This fixture automatically runs for all E2E tests that inherit from this base class.
        It extracts user info from auth headers and makes it available as instance variables.

        Sets:
            self.user_id: The authenticated user's ID
            self.auth_headers: The authentication headers dict
        """
        user_info = self.get_user_from_auth_headers(auth_headers)
        self.user_id = user_info["id"]
        self.auth_headers = auth_headers
        yield

    def get_user_from_token(self, token: str) -> dict:
        """
        Helper method to get user info from auth token by decoding JWT directly.

        Args:
            token: JWT token string

        Returns:
            Dict with user information (id, email, etc.)
        """
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_info = {
                "id": decoded.get("sub", ""),
                "email": decoded.get("email", ""),
                "first_name": decoded.get("first_name"),
                "last_name": decoded.get("last_name"),
            }
            return user_info
        except Exception as e:
            print(f"Error decoding JWT: {str(e)}")
            raise ValueError(f"Failed to extract user info from token: {str(e)}")

    def get_user_from_auth_headers(self, auth_headers: dict) -> dict:
        """
        Helper method to extract user info from auth headers.

        Args:
            auth_headers: Dict with Authorization header

        Returns:
            Dict with user information
        """
        auth_value = auth_headers.get("Authorization", "")
        if auth_value.startswith("Bearer "):
            token = auth_value.split(" ", 1)[1]
            return self.get_user_from_token(token)
        raise ValueError("Invalid Authorization header format")
