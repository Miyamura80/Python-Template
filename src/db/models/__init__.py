# To make this a package, we need to have an __init__.py file

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine as create_raw_engine


# These definitions have to be before the imports, because we use them in the definition of underlying models
# Create declarative base for SQLAlchemy 2.0 style
class Base(AsyncAttrs, DeclarativeBase):  # type: ignore
    pass


def transfer_rls_policies_to_tables():
    """
    Transfer RLS policies from model classes to table metadata.

    This should be called after all models are imported to ensure that
    RLS policies are available during Alembic autogeneration.
    """
    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table = mapper.local_table

        # Check if this model has RLS policies defined
        if hasattr(model_class, "__rls_policies__"):
            # Store RLS policies in the table's info dictionary
            table.info["rls_policies"] = model_class.__rls_policies__  # type: ignore
            print(
                f"📋 Transferred {len(model_class.__rls_policies__)} RLS policies for {table.name}"  # type: ignore
            )  # type: ignore


default_schema = "public"

from common.global_config import global_config  # noqa


# Import all models so Alembic can detect them
# Using automated model discovery system
from src.db.utils.model_discovery import discover_models  # noqa

# Discover all models automatically
_discovered_models = discover_models()

# Manual imports for backward compatibility and explicit control
from src.db.models.auth.users import User  # noqa


# Transfer RLS policies from model classes to table metadata
# This needs to happen after all models are imported
transfer_rls_policies_to_tables()


def get_raw_engine() -> Engine:
    # Create raw SQLAlchemy engine for non-Flask contexts
    # Sync engine.
    raw_engine = create_raw_engine(global_config.database_uri)
    return raw_engine


# Make models available for import
__all__ = [
    "Base",
    "default_schema",
    "get_raw_engine",
    "User",
    "APIKey",
]
