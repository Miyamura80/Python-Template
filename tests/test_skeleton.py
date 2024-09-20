import unittest

from tests.test_class import TestCaseClass, ci_test
from global_config import global_config


class TestSkeleton(TestCaseClass):
    def setUp(self) -> None:
        super().setUp()

    @ci_test
    def test_function(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
