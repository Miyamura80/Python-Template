#!/usr/bin/env python3
"""
Model Validation Script

Simple script to validate database models and dependencies before migration.
This script is designed to be called from the Makefile.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.utils.migration_validator import (
    validate_migration_readiness,
    MigrationValidationError,
)
from loguru import logger as log
from src.utils.logging_config import setup_logging

# Setup logging
setup_logging()


def main():
    """Main validation function."""
    try:
        log.info("🔍 Starting model validation...")

        # Run validation with minimal output for Makefile
        success = validate_migration_readiness(
            strict=False,  # Don't treat warnings as errors for quick validation
            verbose=False,  # Minimal output for Makefile
        )

        if success:
            log.info("✅ Model validation passed")
            return 0
        else:
            log.error("❌ Model validation failed")
            return 1

    except MigrationValidationError as e:
        log.error(f"❌ Migration validation error: {e}")
        return 1
    except Exception as e:
        log.error(f"❌ Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
