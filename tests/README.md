# Tests

## Writing tests

Tests are written using pytest. To add a new test, create a new file/directory in the `tests` directory.




## Running tests

To run the tests, you can use the following commands:

1. For deterministic tests (Run in CI):
   ```bash
   make test
   ```



These commands use `uv` to execute the tests. Make sure you have `uv` installed and your Python dependencies are up to date. You can update dependencies by running:

```bash
uv sync
```