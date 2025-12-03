import pytest
from unittest.mock import MagicMock
from src.utils import version
import importlib.metadata

@pytest.fixture(autouse=True)
def mock_global_config(monkeypatch):
    mock_config = MagicMock()
    mock_config.cli.package_name = "eito-cli"
    mock_config.cli.local_package_name = "python-template"
    monkeypatch.setattr("src.utils.version.global_config", mock_config)

class TestVersionCheck:
    def test_get_current_version_success(self, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda x: "0.1.0")
        assert version.get_current_version() == "0.1.0"

    def test_get_current_version_fallback(self, monkeypatch):
        def mock_version(name):
            if name == "eito-cli":
                raise importlib.metadata.PackageNotFoundError
            if name == "python-template":
                return "0.1.0"
            raise importlib.metadata.PackageNotFoundError

        monkeypatch.setattr(importlib.metadata, "version", mock_version)
        assert version.get_current_version() == "0.1.0"

    def test_get_latest_version_success(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "0.2.0"}}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        monkeypatch.setattr("src.utils.version.requests", mock_requests)

        assert version.get_latest_version() == "0.2.0"

    def test_is_update_available_true(self, monkeypatch):
        monkeypatch.setattr("src.utils.version.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("src.utils.version.get_latest_version", lambda: "0.2.0")
        monkeypatch.setattr("src.utils.version.get_cached_latest_version", lambda: None)
        monkeypatch.setattr("src.utils.version.save_cached_latest_version", lambda x: None)

        available, current, latest = version.is_update_available()
        assert available is True
        assert current == "0.1.0"
        assert latest == "0.2.0"

    def test_is_update_available_false(self, monkeypatch):
        monkeypatch.setattr("src.utils.version.get_current_version", lambda: "0.2.0")
        monkeypatch.setattr("src.utils.version.get_latest_version", lambda: "0.2.0")
        monkeypatch.setattr("src.utils.version.get_cached_latest_version", lambda: None)
        monkeypatch.setattr("src.utils.version.save_cached_latest_version", lambda x: None)

        available, current, latest = version.is_update_available()
        assert available is False

    def test_is_update_available_fail(self, monkeypatch):
        monkeypatch.setattr("src.utils.version.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("src.utils.version.get_latest_version", lambda: None)
        monkeypatch.setattr("src.utils.version.get_cached_latest_version", lambda: None)
        monkeypatch.setattr("src.utils.version.save_cached_latest_version", lambda x: None)

        available, current, latest = version.is_update_available()
        assert available is False

    def test_is_update_available_cached(self, monkeypatch):
        monkeypatch.setattr("src.utils.version.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("src.utils.version.get_cached_latest_version", lambda: "0.3.0")
        # get_latest_version should NOT be called
        mock_get_latest = MagicMock()
        monkeypatch.setattr("src.utils.version.get_latest_version", mock_get_latest)

        available, current, latest = version.is_update_available()
        assert available is True
        assert latest == "0.3.0"
        mock_get_latest.assert_not_called()
