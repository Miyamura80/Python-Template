"""
E2E tests for agent endpoint
"""

import warnings
import json
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

    def test_agent_basic_message(self):
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
        assert "conversation_id" in data

        # Verify user_id matches
        assert data["user_id"] == self.user_id

        # Verify response is not empty
        assert len(data["response"]) > 0

        log.info(f"Agent response: {data['response'][:100]}...")

    def test_agent_with_context(self):
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
        assert "conversation_id" in data

        # Verify response is not empty
        assert len(data["response"]) > 0

        log.info(f"Agent response with context: {data['response'][:100]}...")

    def test_agent_without_optional_context(self):
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
        assert "conversation_id" in data

        log.info(f"Agent response without context: {data['response'][:100]}...")

    def test_agent_empty_message_validation(self):
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

    def test_agent_missing_message_field(self):
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

    def test_agent_invalid_json(self):
        """Test agent endpoint with invalid JSON"""
        log.info("Testing agent endpoint with invalid JSON")

        response = self.client.post(
            "/agent",
            data="not valid json",
            headers=self.auth_headers,
        )

        # Should fail with 422 for invalid JSON
        assert response.status_code == 422

    def test_agent_complex_message(self):
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
        assert "conversation_id" in data
        assert "conversation" in data
        assert data["conversation"]["title"]
        assert len(data["conversation"]["conversation"]) >= 2
        assert data["conversation"]["conversation"][0]["role"] == "user"

        # Verify response is substantial for a complex query
        assert len(data["response"]) > 50

        log.info(f"Agent response to complex message: {data['response'][:150]}...")

    def test_agent_history_returns_conversations(self):
        """Test that chat history returns previous conversations."""
        log.info("Testing agent history endpoint")

        send_response = self.client.post(
            "/agent",
            json={"message": "History check message"},
            headers=self.auth_headers,
        )
        assert send_response.status_code == 200
        conversation_id = send_response.json()["conversation_id"]

        history_response = self.client.get(
            "/agent/history",
            headers=self.auth_headers,
        )

        assert history_response.status_code == 200
        history_data = history_response.json()

        assert "history" in history_data
        assert len(history_data["history"]) >= 1

        matching_conversation = next(
            (c for c in history_data["history"] if c["id"] == conversation_id),
            None,
        )
        assert matching_conversation is not None
        assert matching_conversation["title"]
        assert len(matching_conversation["conversation"]) >= 2
        assert matching_conversation["conversation"][0]["role"] == "user"

    def test_agent_stream_requires_authentication(self):
        """Test that agent streaming endpoint requires authentication"""
        response = self.client.post(
            "/agent/stream",
            json={"message": "Hello, agent!"},
        )

        # Should fail without authentication
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_agent_stream_basic_message(self):
        """Test agent streaming endpoint with a basic message"""
        log.info("Testing agent streaming endpoint with basic message")

        response = self.client.post(
            "/agent/stream",
            json={"message": "What is 2 + 2?"},
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse the streaming response
        chunks = []
        start_received = False
        done_received = False

        # Split by double newline to get individual SSE messages
        messages = response.text.strip().split("\n\n")

        for message in messages:
            if message.startswith("data: "):
                data = json.loads(message[6:])  # Skip "data: " prefix
                chunks.append(data)

                if data["type"] == "start":
                    start_received = True
                    assert "user_id" in data
                    assert data["user_id"] == self.user_id
                    assert "conversation_id" in data
                    assert data.get("conversation_title")
                    assert data.get("tools_enabled") is not None
                    assert isinstance(data.get("tool_names"), list)
                elif data["type"] == "token":
                    assert "content" in data
                elif data["type"] == "done":
                    done_received = True
                elif data["type"] == "warning":
                    assert data.get("code") == "tool_fallback"

        # Verify we received start and done signals
        assert start_received, "Should receive start signal"
        assert done_received, "Should receive done signal"

        # Verify we received some tokens
        token_chunks = [c for c in chunks if c["type"] == "token"]
        assert len(token_chunks) > 0, "Should receive at least one token"

        # Reconstruct the full response
        full_response = "".join([c["content"] for c in token_chunks])
        assert len(full_response) > 0, "Response should not be empty"

        log.info(f"Agent streaming response: {full_response[:100]}...")

    def test_agent_stream_with_context(self):
        """Test agent streaming endpoint with additional context"""
        log.info("Testing agent streaming endpoint with context")

        response = self.client.post(
            "/agent/stream",
            json={
                "message": "Tell me about Python",
                "context": "I am a beginner programmer",
            },
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse and verify streaming response
        messages = response.text.strip().split("\n\n")
        chunks = []

        for message in messages:
            if message.startswith("data: "):
                data = json.loads(message[6:])
                chunks.append(data)

        # Verify structure
        start_event = next(c for c in chunks if c["type"] == "start")
        assert "tools_enabled" in start_event
        assert "tool_names" in start_event
        assert "conversation_id" in start_event
        assert any(c["type"] == "start" for c in chunks)
        assert any(c["type"] == "done" for c in chunks)
        token_chunks = [c for c in chunks if c["type"] == "token"]
        assert len(token_chunks) > 0

        full_response = "".join([c["content"] for c in token_chunks])
        log.info(f"Agent streaming response with context: {full_response[:100]}...")

    def test_agent_stream_missing_message_field(self):
        """Test that agent streaming endpoint requires message field"""
        log.info("Testing agent streaming endpoint without message field")

        response = self.client.post(
            "/agent/stream",
            json={},
            headers=self.auth_headers,
        )

        # Should fail validation
        assert response.status_code == 422
        assert "field required" in response.json()["detail"][0]["msg"].lower()

    def test_agent_stream_persists_history(self):
        """Test that streaming responses are stored in history."""
        log.info("Testing streaming history persistence")

        stream_response = self.client.post(
            "/agent/stream",
            json={"message": "Persist this streaming response"},
            headers=self.auth_headers,
        )

        assert stream_response.status_code == 200
        messages = stream_response.text.strip().split("\n\n")

        conversation_id = None
        token_chunks = []

        for message in messages:
            if not message.startswith("data: "):
                continue
            data = json.loads(message[6:])

            if data["type"] == "start":
                conversation_id = data["conversation_id"]
            elif data["type"] == "token":
                token_chunks.append(data["content"])

        assert conversation_id is not None
        assert len(token_chunks) > 0

        full_response = "".join(token_chunks)
        assert len(full_response) > 0

        history_response = self.client.get(
            "/agent/history",
            headers=self.auth_headers,
        )

        assert history_response.status_code == 200
        history_data = history_response.json()
        conversation = next(
            (c for c in history_data["history"] if c["id"] == conversation_id),
            None,
        )

        assert conversation is not None
        assert len(conversation["conversation"]) >= 2
        assert conversation["conversation"][0]["role"] == "user"
        assert conversation["conversation"][-1]["role"] == "assistant"
        assert conversation["conversation"][-1]["content"] == full_response
