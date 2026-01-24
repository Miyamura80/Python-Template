from copy import deepcopy

import pytest
from human_id import generate_id

from common import global_config

# Markers for slow, and nondeterministic tests
slow_test = pytest.mark.slow
nondeterministic_test = pytest.mark.nondeterministic
slow_and_nondeterministic_test = pytest.mark.slow_and_nondeterministic


class TestTemplate:
    @pytest.fixture(autouse=True)
    def setup(self, test_config=None):
        running_on = global_config.running_on

        setup_message = (
            f"🧪 Setting up \033[34mTestTemplate\033[0m "
            f"from {__name__}"
            f" on {running_on} machine..."
        )
        print(setup_message)

        # Use common if no test_config is provided
        config = deepcopy(
            test_config if test_config is not None else global_config.to_dict()
        )

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

        self.config = config

    @pytest.fixture(scope="session", autouse=True)
    def session_teardown(self, request):
        yield  # This line is important - it allows the tests to run
        # Code after this yield will run after all tests are complete
        print("\n🏁 All tests have completed running.")
        # You can add any other teardown or summary code here
