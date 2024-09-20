import unittest
import os
import sys
import yaml
from human_id import generate_id
from global_config import global_config

from dotenv import load_dotenv

with open("tests/config.yaml", "r", encoding="utf-8") as config_file:
    config = yaml.safe_load(config_file)


def ci_test(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        print(f"✅\033[0;32m Successfully ran {self._testMethodName}\033[0m")
        return result

    return wrapper


class TestCaseClass(unittest.TestCase):
    def setUp(self) -> None:
        is_local = os.getenv("GITHUB_ACTIONS") != "true"
        running_on = "🖥️  local" if is_local else "☁️  CI"

        # If it is not a github action, load the dotenv
        if is_local:
            load_dotenv()
            _openai_api_key = os.getenv("OPENAI_API_KEY")

        setup_message = (
            f"🧪 Setting up \033[34m{self.__class__.__name__}\033[0m "
            f"from {self.__class__.__module__}"
            f" on {running_on} machine..."
        )
        print(setup_message)

        # Set the session id to the class name and a random id
        self.session_id = f"{self.__class__.__name__}-@-{generate_id()}"
        config["session_id"] = self.session_id

        # Set the session name to "Unit Tests using LLMs"
        self.session_name = f"Unit Tests using LLMs"
        config["session_name"] = self.session_name

        # Set the session path to /tests
        self.session_path = f"/tests"
        config["session_path"] = self.session_path

        # Set test to true
        config["test"] = True

        self.config = config


if __name__ == "__main__":
    unittest.main()
