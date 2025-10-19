"""
E2E tests for ping endpoint
"""

import pytest
from datetime import datetime
from tests.e2e.e2e_test_base import E2ETestBase


class TestPing(E2ETestBase):
    """Tests for the ping endpoint"""

    @pytest.fixture(autouse=True)
    def setup_shared_variables(self, setup):
        """Initialize shared attributes"""
        pass

    def test_ping_endpoint_returns_pong(self):
        """Test that ping endpoint returns expected pong response"""
        response = self.client.get("/ping")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "status" in data
        assert "timestamp" in data
        
        # Verify response values
        assert data["message"] == "pong"
        assert data["status"] == "ok"

    def test_ping_endpoint_timestamp_format(self):
        """Test that ping endpoint returns valid ISO format timestamp"""
        response = self.client.get("/ping")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamp is valid ISO format
        timestamp_str = data["timestamp"]
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp_str)
            assert parsed_timestamp is not None
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp_str}' is not valid ISO format")

    def test_ping_endpoint_no_auth_required(self):
        """Test that ping endpoint does not require authentication"""
        # Make request without auth headers
        response = self.client.get("/ping")
        
        # Should still succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
        assert data["status"] == "ok"

    def test_ping_endpoint_multiple_calls(self):
        """Test that ping endpoint can be called multiple times"""
        # Make multiple calls to ensure endpoint is stable
        for _ in range(5):
            response = self.client.get("/ping")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "pong"
            assert data["status"] == "ok"

