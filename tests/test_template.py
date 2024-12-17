import pytest
import os
from copy import deepcopy
from human_id import generate_id

# Markers for slow, and nondeterministic tests
slow_test = pytest.mark.slow
nondeterministic_test = pytest.mark.nondeterministic
slow_and_nondeterministic_test = pytest.mark.slow_and_nondeterministic


class TestTemplate:
    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        is_local = os.getenv("GITHUB_ACTIONS") != "true"
        running_on = "🖥️  local" if is_local else "☁️  CI"

        setup_message = (
            f"🧪 Setting up \033[34mTestTemplate\033[0m "
            f"from {__name__}"
            f" on {running_on} machine..."
        )
        print(setup_message)

        config = deepcopy(test_config)

        # Set the session id to the class name and a random id
        config["session_id"] = f"TestTemplate-@-{generate_id()}"

        # Set the session name to "Unit Tests using LLMs"
        config["session_name"] = "Unit Tests using LLMs"

        # Set the session path to /tests
        config["session_path"] = "/tests"

        # Set test to true
        config["test"] = True

        for key, value in config.items():
            setattr(self, key, value)

    @pytest.fixture(scope="session", autouse=True)
    def session_teardown(self, request):
        yield  # This line is important - it allows the tests to run
        # Code after this yield will run after all tests are complete
        print("\n🏁 All tests have completed running.")
        # You can add any other teardown or summary code here
