"""
E2E tests for agent endpoint
"""

import warnings
from tests.e2e.e2e_test_base import E2ETestBase
from loguru import logger as log
from src.utils.logging_config import setup_logging

# Suppress common warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
warnings.filterwarnings(
    "ignore",
    message=".*class-based.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*class-based `config` is deprecated.*",
    category=Warning,
)

setup_logging()


class TestAgent(E2ETestBase):
    """Tests for the agent endpoint"""

    def test_agent_requires_authentication(self):
        """Test that agent endpoint requires authentication"""
        response = self.client.post(
            "/agent",
            json={"message": "Hello, agent!"},
        )

        # Should fail without authentication
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_agent_basic_message(self, setup_test_user):
        """Test agent endpoint with a basic message"""
        log.info("Testing agent endpoint with basic message")

        response = self.client.post(
            "/agent",
            json={"message": "What is 2 + 2?"},
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "user_id" in data
        assert "reasoning" in data

        # Verify user_id matches
        assert data["user_id"] == self.user_id

        # Verify response is not empty
        assert len(data["response"]) > 0

        log.info(f"Agent response: {data['response'][:100]}...")

    def test_agent_with_context(self, setup_test_user):
        """Test agent endpoint with additional context"""
        log.info("Testing agent endpoint with context")

        response = self.client.post(
            "/agent",
            json={
                "message": "Can you help me with my project?",
                "context": "I am working on a Python web application",
            },
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "user_id" in data

        # Verify response is not empty
        assert len(data["response"]) > 0

        log.info(f"Agent response with context: {data['response'][:100]}...")

    def test_agent_without_optional_context(self, setup_test_user):
        """Test agent endpoint without optional context"""
        log.info("Testing agent endpoint without optional context")

        response = self.client.post(
            "/agent",
            json={"message": "Tell me a joke"},
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "user_id" in data

        log.info(f"Agent response without context: {data['response'][:100]}...")

    def test_agent_empty_message_validation(self, setup_test_user):
        """Test that agent endpoint validates empty messages"""
        log.info("Testing agent endpoint with empty message")

        response = self.client.post(
            "/agent",
            json={"message": ""},
            headers=self.auth_headers,
        )

        # Empty string is technically valid in Pydantic, but the agent should handle it
        # If validation is added, this would return 422
        # For now, just verify it doesn't crash
        assert response.status_code in [200, 422]

    def test_agent_missing_message_field(self, setup_test_user):
        """Test that agent endpoint requires message field"""
        log.info("Testing agent endpoint without message field")

        response = self.client.post(
            "/agent",
            json={},
            headers=self.auth_headers,
        )

        # Should fail validation
        assert response.status_code == 422
        assert "field required" in response.json()["detail"][0]["msg"].lower()

    def test_agent_invalid_json(self, setup_test_user):
        """Test agent endpoint with invalid JSON"""
        log.info("Testing agent endpoint with invalid JSON")

        response = self.client.post(
            "/agent",
            data="not valid json",
            headers=self.auth_headers,
        )

        # Should fail with 422 for invalid JSON
        assert response.status_code == 422

    def test_agent_complex_message(self, setup_test_user):
        """Test agent endpoint with a complex multi-part message"""
        log.info("Testing agent endpoint with complex message")

        complex_message = """
        I need help with the following:
        1. Understanding how to structure my database
        2. Setting up authentication
        3. Deploying to production
        
        Can you provide guidance on these topics?
        """

        response = self.client.post(
            "/agent",
            json={"message": complex_message},
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "user_id" in data

        # Verify response is substantial for a complex query
        assert len(data["response"]) > 50

        log.info(f"Agent response to complex message: {data['response'][:150]}...")
