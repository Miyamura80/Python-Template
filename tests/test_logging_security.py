import pytest

from src.utils.logging_config import scrub_sensitive_data
from tests.test_template import TestTemplate


class TestLoggingSecurity(TestTemplate):
    @pytest.fixture(autouse=True)
    def setup_shared_variables(self, setup):
        # Initialize shared attributes here
        pass

    def test_email_redaction(self):
        """Test that email addresses are redacted from log messages."""
        record = {"message": "User email is test@example.com", "exception": None}
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert "test@example.com" not in message
        assert "{{EMAIL}}" in message

    def test_phone_redaction(self):
        """Test that phone numbers are redacted (new capability via scrubadub)."""
        record = {"message": "Call me at 1-800-555-0199", "exception": None}
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert "1-800-555-0199" not in message
        assert "{{PHONE}}" in message

    def test_api_key_redaction(self):
        """Test that OpenAI API keys are redacted from log messages."""
        api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901"
        record = {"message": f"Using key: {api_key}", "exception": None}
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert api_key not in message
        assert "[REDACTED_API_KEY]" in message

    def test_multiple_redactions(self):
        """Test redacting multiple sensitive items in a single message."""
        record = {
            "message": "Email test@example.com and key sk-123456789012345678901234",
            "exception": None,
        }
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert "{{EMAIL}}" in message
        assert "[REDACTED_API_KEY]" in message
        assert "test@example.com" not in message
        assert "sk-123456789012345678901234" not in message

    def test_exception_message_redaction(self):
        """Test that PII is redacted from exception messages."""
        # Mocking the exception tuple structure used by loguru: (type, value, traceback)
        exception_value = ValueError("Failed for user test@example.com")
        record = {
            "message": "An error occurred",
            "exception": (ValueError, exception_value, None),
        }

        scrub_sensitive_data(record)

        # Verify message (even if it didn't have PII)
        assert record["message"] == "An error occurred"

        # Verify exception redaction
        _, value, _ = record["exception"]
        assert "test@example.com" not in str(value)
        assert "{{EMAIL}}" in str(value)

    def test_exception_api_key_redaction(self):
        """Test redacting API keys from exception values."""
        api_key = "sk-123456789012345678901234"
        exception_value = Exception(f"Auth failed with {api_key}")
        record = {"message": "Error", "exception": (Exception, exception_value, None)}

        scrub_sensitive_data(record)

        _, value, _ = record["exception"]
        assert api_key not in str(value)
        assert "[REDACTED_API_KEY]" in str(value)

    def test_no_sensitive_data_unchanged(self):
        """Test that normal messages are left untouched."""
        original_message = "Normal system message"
        record = {"message": original_message, "exception": None}
        scrub_sensitive_data(record)
        assert record["message"] == original_message

    def test_anthropic_api_key_redaction(self):
        """Test that Anthropic API keys are redacted."""
        api_key = "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678"
        record = {"message": f"Using Anthropic key: {api_key}", "exception": None}
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert api_key not in message
        assert "[REDACTED_API_KEY]" in message

    def test_stripe_api_key_redaction(self):
        """Test that Stripe API keys are redacted."""
        # Construct keys dynamically to avoid GitHub secret scanning
        suffix = "0" * 24
        prefixes = ["sk" + "_live_", "sk" + "_test_", "pk" + "_live_", "rk" + "_live_"]

        for prefix in prefixes:
            key = prefix + suffix
            record = {"message": f"Stripe key: {key}", "exception": None}
            scrub_sensitive_data(record)
            message = record["message"]
            assert isinstance(message, str)
            assert key not in message
            assert "[REDACTED_API_KEY]" in message

    def test_bearer_token_redaction(self):
        """Test that Authorization Bearer tokens are redacted."""
        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkw"
        record = {"message": f"Authorization: {token}", "exception": None}
        scrub_sensitive_data(record)
        message = record["message"]
        assert isinstance(message, str)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in message
        assert "[REDACTED_BEARER_TOKEN]" in message

    def test_generic_api_key_redaction(self):
        """Test that generic api_key patterns are redacted."""
        patterns = [
            "api_key=abc123def456ghi789jkl012",
            "API-KEY: abc123def456ghi789jkl012",
            "apikey='abc123def456ghi789jkl012'",
            "project_key=abc123def456ghi789jkl012",
            "secret-key: abc123def456ghi789jkl012",
        ]
        for pattern in patterns:
            record = {"message": f"Config: {pattern}", "exception": None}
            scrub_sensitive_data(record)
            message = record["message"]
            assert isinstance(message, str)
            assert "abc123def456ghi789jkl012" not in message
            assert "[REDACTED_KEY]" in message
