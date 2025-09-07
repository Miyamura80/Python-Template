"""
Automated Model Discovery System

This module provides functionality to automatically discover and import SQLAlchemy models
from the models directory, eliminating the need for manual import management.
"""

import importlib
import inspect
from pathlib import Path
from typing import Type, Set
from sqlalchemy.orm import DeclarativeBase

from loguru import logger as log
from src.utils.logging import setup_logging

# Setup logging
setup_logging()


def discover_models(models_root: str = "src.db.models") -> list[Type[DeclarativeBase]]:
    """
    Automatically discover and import all SQLAlchemy models from the models directory.

    Args:
        models_root: Root module path for models (default: "src.db.models")

    Returns:
        List of discovered model classes

    Raises:
        ImportError: If a model module cannot be imported
    """
    log.info(f"Starting model discovery from {models_root}")

    models: list[Type[DeclarativeBase]] = []

    # Get the models directory path
    models_dir = Path(__file__).parent.parent / "models"
    if not models_dir.exists():
        log.error(f"Models directory not found: {models_dir}")
        return models

    # Discover all Python files in subdirectories
    for schema_dir in models_dir.iterdir():
        if not schema_dir.is_dir() or schema_dir.name.startswith("__"):
            continue

        log.trace(f"Scanning schema directory: {schema_dir.name}")

        for model_file in schema_dir.glob("*.py"):
            if model_file.stem.startswith("__"):
                continue

            module_name = f"{models_root}.{schema_dir.name}.{model_file.stem}"
            log.trace(f"Importing module: {module_name}")

            try:
                module = importlib.import_module(module_name)

                # Find all classes that inherit from DeclarativeBase
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        hasattr(obj, "__tablename__")
                        and hasattr(obj, "__table__")
                        and obj.__module__ == module_name
                    ):
                        models.append(obj)
                        log.trace(f"Discovered model: {name} from {module_name}")

            except Exception as e:
                log.error(f"Failed to import {module_name}: {e}")
                raise ImportError(f"Failed to import model module {module_name}: {e}")

    log.debug(f"Successfully discovered {len(models)} models")
    return models


def get_all_models() -> dict[str, Type[DeclarativeBase]]:
    """
    Get all models as a dictionary mapping model names to classes.

    Returns:
        Dictionary mapping model names to model classes
    """
    models = discover_models()
    return {model.__name__: model for model in models}


def get_model_dependencies() -> dict[str, Set[str]]:
    """
    Analyze model dependencies based on foreign key relationships.

    Returns:
        Dictionary mapping model names to sets of models they depend on
    """
    log.info("Analyzing model dependencies")

    models = get_all_models()
    dependencies: dict[str, Set[str]] = {}

    for model_name, model_class in models.items():
        dependencies[model_name] = set()

        # Check foreign key constraints
        if hasattr(model_class, "__table__"):
            for fk in model_class.__table__.foreign_keys:
                # Extract referenced table name
                referenced_table = fk.column.table.name

                # Find the model that owns this table
                for other_model_name, other_model_class in models.items():
                    if (
                        hasattr(other_model_class, "__tablename__")
                        and other_model_class.__tablename__ == referenced_table
                    ):
                        dependencies[model_name].add(other_model_name)
                        break

    log.trace(f"Model dependencies: {dependencies}")
    return dependencies


def validate_import_completeness() -> bool:
    """
    Validate that all models can be imported and discovered.

    Returns:
        True if all models can be imported, False otherwise
    """
    log.info("Validating import completeness")

    try:
        models = discover_models()

        if not models:
            log.warning("No models discovered - this might indicate an issue")
            return False

        # Check that all models have required attributes
        for model in models:
            if not hasattr(model, "__tablename__"):
                log.error(f"Model {model.__name__} missing __tablename__")
                return False

            if not hasattr(model, "__table__"):
                log.error(f"Model {model.__name__} missing __table__")
                return False

        log.info("All models imported successfully")
        return True

    except Exception as e:
        log.error(f"Import validation failed: {e}")
        return False


def get_missing_imports() -> list[str]:
    """
    Identify any model files that exist but aren't being imported.

    Returns:
        List of model files that couldn't be imported
    """
    log.info("Checking for missing imports")

    models_dir = Path(__file__).parent.parent / "models"
    missing_imports: list[str] = []

    for schema_dir in models_dir.iterdir():
        if not schema_dir.is_dir() or schema_dir.name.startswith("__"):
            continue

        for model_file in schema_dir.glob("*.py"):
            if model_file.stem.startswith("__"):
                continue

            module_name = f"src.db.models.{schema_dir.name}.{model_file.stem}"

            try:
                importlib.import_module(module_name)
            except Exception as e:
                missing_imports.append(f"{module_name}: {e}")
                log.warning(f"Could not import {module_name}: {e}")

    return missing_imports