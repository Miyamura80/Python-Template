from loguru import logger as log
from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryProvider

from common.global_config import global_config


def setup_feature_flags():
    """
    Initialize OpenFeature with flags from global configuration.
    This uses the InMemoryProvider, effectively loading flags from:
    1. Environment variables (FEATURES__FLAG_NAME=true)
    2. global_config.yaml (features: flag_name: true)
    """
    # Convert Pydantic model to dict, allowing extra fields
    flags = global_config.features.model_dump()

    # Initialize the provider
    provider = InMemoryProvider(flags)
    api.set_provider(provider)

    log.debug("Feature flags initialized: {}", list(flags.keys()))


# Optionally auto-initialize when imported
# To defer initialization, import setup_feature_flags and call it explicitly
setup_feature_flags()
client = api.get_client()
