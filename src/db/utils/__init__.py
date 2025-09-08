"""
Database Utilities Module

This module provides utilities for database model management, migration validation,
and dependency management to prevent common migration issues.

Submodules:
- model_discovery: Automated model discovery and import management
- dependency_validator: Validates model dependencies and detects circular references
- foreign_key_manager: Utilities for proper foreign key definition with use_alter detection
- migration_validator: Pre-migration validation checks
"""

from .model_discovery import discover_models, get_all_models
from .dependency_validator import validate_model_dependencies, DependencyValidationError
from .foreign_key_manager import ForeignKeyManager, create_foreign_key_constraint
from .migration_validator import validate_migration_readiness

__all__ = [
    "discover_models",
    "get_all_models", 
    "validate_model_dependencies",
    "DependencyValidationError",
    "ForeignKeyManager",
    "create_foreign_key_constraint",
    "validate_migration_readiness",
] 