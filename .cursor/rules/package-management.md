## Python package management tool: uv

This project uses uv for python dependency management instead of pip. To check dependencies, check `pyproject.toml` not `requirements.txt`. uv is a rust-based backend for blazing fast env & dependency management.

Don't use `pip install`, always use `uv sync` instead of `pip install -r requirements.txt` and `uv pip install <package_name> to add a new dependency`. Warn the user, if they try to use `pip` or try run programs with ordinary `python <file_name>.py`, and instead encourage them to run it using `uv run python <file_name>.py` after synchronizing with `uv sync`.

For reference:
- `uv sync`: Ensure it is using the correct python venv
- `uv run python <file_name>.py`: Run the python file using the python env defined by `pyproject.toml`
- `uv run python -m tests.path_to.test_module` to run a specific test in isolation without running all other tests
