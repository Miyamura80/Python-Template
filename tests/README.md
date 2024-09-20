# Tests

## Writing tests

Tests are written using pytest. To add a new test, create a new file/directory in the `tests` directory.

### Test structure

Look at `tests/test_skeleton.py` for an example test structure. On how you should write tests.

```python
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

```

Few things to note:
- Every test file should inherit from `TestCaseClass`. (Look at `tests/test_class.py`) This ensures that the test environment is set up correctly.
- Every test file should contain a `setUp` method that sets up the test environment.
- Each test class should have a `self.config` variable that is used to configure the test. (Look at `tests/config.yaml`. This is what it loads into a dictionary.) `self.config` also contains a `session_id` and `session_path` variable, which is the path to the session directory. This is where all the logs and artifacts are saved.
- Each test should be prefixed with `test_` so that pytest can identify and run them. Put a `@ci_test` decorator on every test that should be run in CI. (Look at `tests/test_class.py`)
- (Optional) If you want the global config found in `global_config/global_config.yaml`, import using:
    ```python
    from global_config import global_config
    ```




## Running tests

To run the tests, you can use the following commands:

1. For deterministic tests (Run in CI):
   ```bash
   make test
   ```



These commands use `rye run pytest` to execute the tests. Make sure you have `rye` installed and your Python dependencies are up to date. You can update dependencies by running:

```bash
rye sync
```