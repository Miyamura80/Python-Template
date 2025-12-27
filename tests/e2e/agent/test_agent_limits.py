"""
E2E tests for agent limits endpoint
"""

from tests.e2e.e2e_test_base import E2ETestBase
from loguru import logger as log
from src.utils.logging_config import setup_logging
from datetime import datetime

setup_logging()


class TestAgentLimits(E2ETestBase):
    """Tests for the agent limits endpoint"""

    def test_get_agent_limits(self):
        """Test getting agent limits"""
        log.info("Testing get agent limits endpoint")

        response = self.client.get(
            "/agent/limits",
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "tier" in data
        assert "limit_name" in data
        assert "limit_value" in data
        assert "used_today" in data
        assert "remaining" in data
        assert "reset_at" in data

        # Verify types
        assert isinstance(data["tier"], str)
        assert isinstance(data["limit_name"], str)
        assert isinstance(data["limit_value"], int)
        assert isinstance(data["used_today"], int)
        assert isinstance(data["remaining"], int)

        # Verify reset_at is a valid datetime string
        try:
            datetime.fromisoformat(data["reset_at"])
        except ValueError:
            assert False, "reset_at is not a valid ISO format string"

        log.info(f"Agent limits response: {data}")

    def test_get_agent_limits_unauthenticated(self):
        """Test getting agent limits without authentication"""
        response = self.client.get("/agent/limits")
        assert response.status_code == 401
