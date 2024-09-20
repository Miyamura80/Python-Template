import os
from typing import Any, Dict
import yaml

# Optionally load .env file
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")

    def __init__(self):
        with open("global_config/global_config.yaml", "r") as file:
            self.global_config = yaml.safe_load(file)

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("__")
        }

    def __getattr__(self, name):
        if name in self.global_config:
            return self.global_config[name]
        raise AttributeError(f"'Config' object has no attribute '{name}'")


# Create a singleton instance
global_config = Config()
