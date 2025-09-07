from tests.test_template import TestTemplate
from common import global_config


class TestCommonHealthCheck(TestTemplate):
    """Test that the common health check flag is enabled."""

    def test_dot_global_config_health_check_enabled(self):
        """
        Test that the dot_global_config_health_check flag is set to True.

        This test ensures that the .global_config.yaml file is being properly loaded
        and overriding the default value (which is False in global_config.yaml).
        """
        assert global_config.dot_global_config_health_check is True, (
            "The dot_global_config_health_check flag should be set to True in .global_config.yaml. "
            "This indicates that the custom configuration is being properly loaded."
        )
