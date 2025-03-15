# Tests

## Writing tests

Tests are written using pytest. To add a new test, create a new file/directory in the `tests` directory.




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