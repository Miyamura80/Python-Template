
import pytest
import os
from unittest.mock import MagicMock, patch
from src.agent.tools.alert_admin import AdminAgentTools

class TestAdminAgentTools:

    @pytest.fixture
    def mock_requests(self):
        with patch('src.agent.tools.alert_admin.requests') as mock:
            yield mock

    @pytest.fixture
    def tools(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123", "TELEGRAM_CHAT_ID": "456"}):
            return AdminAgentTools()

    def test_alert_admin_success(self, tools, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_requests.post.return_value = mock_response

        result = tools.alert_admin("Something happened")
        assert result['status'] == 'success'

    def test_alert_admin_without_optional_context(self, tools, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_requests.post.return_value = mock_response

        result = tools.alert_admin("Something happened")
        assert result['status'] == 'success'

    def test_alert_admin_telegram_failure(self, tools, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Error"}
        mock_requests.post.return_value = mock_response

        result = tools.alert_admin("Something happened")
        # Ensure it returns a status even on failure
        assert 'status' in result
        assert result['status'] == 'error'

    def test_alert_admin_exception_handling(self, tools, mock_requests):
        mock_requests.post.side_effect = Exception("Network error")

        result = tools.alert_admin("Something happened")
        assert 'status' in result
        assert result['status'] == 'error'

    def test_alert_admin_markdown_special_characters(self, tools, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_requests.post.return_value = mock_response

        result = tools.alert_admin("Message with *special* characters")
        assert result['status'] == 'success'
