import os
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

load_dotenv()


class DictWrapper:
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)


class Config:
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")

    def __init__(self):
        with open("global_config/global_config.yaml", "r") as file:
            config_data = yaml.safe_load(file)
        for key, value in config_data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)

    def __getattr__(self, name):
        raise AttributeError(f"'Config' object has no attribute '{name}'")


# Create a singleton instance
global_config = Config()
