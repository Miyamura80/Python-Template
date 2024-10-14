import os
from typing import Any, Dict
import yaml

# Optionally load .env file
from dotenv import load_dotenv, dotenv_values

load_dotenv()


class DictWrapper:
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)


class Config:
    _env_keys = ["OPENAI_API_KEY", "HELICONE_API_KEY"]

    def __init__(self):
        with open("global_config/global_config.yaml", "r") as file:
            config_data = yaml.safe_load(file)
        for key, value in config_data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)

        # Assert we found all necessary keys
        for key in self._env_keys:
            if os.environ.get(key) is None:
                raise ValueError(f"Environment variable {key} not found")
            else:
                setattr(self, key, os.environ.get(key))

    def __getattr__(self, name):
        raise AttributeError(f"'Config' object has no attribute '{name}'")

    def to_dict(self):
        def unwrap(obj):
            if isinstance(obj, DictWrapper):
                return {k: unwrap(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [unwrap(item) for item in obj]
            else:
                return obj

        return {k: unwrap(v) for k, v in self.__dict__.items()}


# Create a singleton instance
global_config = Config()
