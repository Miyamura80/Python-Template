import unittest

from tests.test_class import TestCaseClass, ci_test
from global_config import global_config


class TestDummy(TestCaseClass):
    def setUp(self) -> None:
        super().setUp()
        # Add any setup code here

    @ci_test
    def test_dummy_function(self):
        # This is a dummy test function
        self.assertTrue(True)

    @ci_test
    def test_global_config_access(self):
        # Test that we can access global config
        self.assertIsNotNone(global_config)
        # You might want to add more specific tests here depending on your global_config structure


if __name__ == "__main__":
    unittest.main()
