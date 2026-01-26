from tests.test_template import TestTemplate
from src.utils.logging_config import scrub_sensitive_data


class TestLoggingSecurity(TestTemplate):
    def test_email_redaction(self):
        """Test that email addresses are redacted from log messages."""
        record = {"message": "User email is test@example.com", "exception": None}
        scrub_sensitive_data(record)
        assert "test@example.com" not in record["message"]
        assert "[REDACTED_EMAIL]" in record["message"]

    def test_api_key_redaction(self):
        """Test that OpenAI API keys are redacted from log messages."""
        api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901"
        record = {"message": f"Using key: {api_key}", "exception": None}
        scrub_sensitive_data(record)
        assert api_key not in record["message"]
        assert "[REDACTED_API_KEY]" in record["message"]

    def test_multiple_redactions(self):
        """Test redacting multiple sensitive items in a single message."""
        record = {
            "message": "Email test@example.com and key sk-123456789012345678901234",
            "exception": None,
        }
        scrub_sensitive_data(record)
        assert "[REDACTED_EMAIL]" in record["message"]
        assert "[REDACTED_API_KEY]" in record["message"]
        assert "test@example.com" not in record["message"]
        assert "sk-123456789012345678901234" not in record["message"]

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
        assert "[REDACTED_EMAIL]" in str(value)

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
