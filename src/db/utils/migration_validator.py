"""
Migration Validation System

This module provides comprehensive pre-migration validation by combining all other
validation utilities to ensure migrations will succeed without issues.
"""

import sys
from pathlib import Path

from loguru import logger as log
from src.utils.logging import setup_logging
from .model_discovery import validate_import_completeness, get_missing_imports
from .dependency_validator import (
    validate_model_dependencies,
    format_validation_report,
    DependencyValidationError,
)
from .foreign_key_manager import ForeignKeyManager

# Setup logging
setup_logging()


class MigrationValidationError(Exception):
    """Exception raised when migration validation fails."""

    pass


def validate_migration_readiness(strict: bool = False, verbose: bool = True) -> bool:
    """
    Comprehensive migration readiness validation.

    Args:
        strict: If True, treat warnings as errors
        verbose: If True, print detailed validation report

    Returns:
        True if migration is ready, False otherwise

    Raises:
        MigrationValidationError: If critical validation issues are found
    """
    log.info("🔍 Starting comprehensive migration validation")

    validation_passed = True
    all_issues: list[str] = []

    # 1. Validate model import completeness
    log.info("1️⃣ Validating model import completeness...")
    try:
        if not validate_import_completeness():
            log.error("❌ Model import validation failed")
            validation_passed = False

            # Get specific missing imports
            missing_imports = get_missing_imports()
            if missing_imports:
                log.error("Missing imports found:")
                for missing in missing_imports:
                    log.error(f"  - {missing}")
                    all_issues.append(f"Missing import: {missing}")
        else:
            log.info("✅ All models imported successfully")
    except Exception as e:
        log.error(f"❌ Model import validation failed with error: {e}")
        validation_passed = False
        all_issues.append(f"Import validation error: {e}")

    # 2. Validate model dependencies
    log.info("2️⃣ Validating model dependencies...")
    try:
        dependency_issues = validate_model_dependencies()

        if dependency_issues:
            # Check for critical errors
            critical_issues = [
                issue for issue in dependency_issues if issue.severity == "error"
            ]
            warning_issues = [
                issue for issue in dependency_issues if issue.severity == "warning"
            ]

            if critical_issues:
                log.error(f"❌ Found {len(critical_issues)} critical dependency issues")
                validation_passed = False

            if warning_issues:
                log.warning(f"⚠️ Found {len(warning_issues)} dependency warnings")
                if strict:
                    log.error("❌ Strict mode: treating warnings as errors")
                    validation_passed = False

            all_issues.extend(
                [
                    f"{issue.severity}: {issue.description}"
                    for issue in dependency_issues
                ]
            )

            if verbose:
                report = format_validation_report(dependency_issues)
                log.info(f"Dependency validation report:\n{report}")
        else:
            log.info("✅ No dependency issues found")
    except DependencyValidationError as e:
        log.error(f"❌ Dependency validation failed: {e}")
        validation_passed = False
        all_issues.append(f"Dependency validation error: {e}")

    # 3. Validate foreign key setup
    log.info("3️⃣ Validating foreign key setup...")
    try:
        fk_manager = ForeignKeyManager()

        # Check each model's foreign key setup
        model_issues: list[tuple[str, str]] = []
        for model_name in fk_manager.models.keys():
            issues = fk_manager.validate_foreign_key_setup(model_name)
            if issues:
                model_issues.extend([(model_name, issue) for issue in issues])

        if model_issues:
            log.error(f"❌ Found {len(model_issues)} foreign key setup issues")
            validation_passed = False

            for model_name, issue in model_issues:
                log.error(f"  - {model_name}: {issue}")
                all_issues.append(f"FK issue in {model_name}: {issue}")
        else:
            log.info("✅ Foreign key setup validation passed")

        # Generate dependency report if verbose
        if verbose:
            dependency_report = fk_manager.get_dependency_report()
            log.info(f"Foreign key dependency report:\n{dependency_report}")
    except Exception as e:
        log.error(f"❌ Foreign key validation failed: {e}")
        validation_passed = False
        all_issues.append(f"Foreign key validation error: {e}")

    # 4. Validate Alembic configuration
    log.info("4️⃣ Validating Alembic configuration...")
    try:
        alembic_issues: list[str] = _validate_alembic_config()
        if alembic_issues:
            log.error(f"❌ Found {len(alembic_issues)} Alembic configuration issues")
            validation_passed = False
            all_issues.extend(alembic_issues)
        else:
            log.info("✅ Alembic configuration validation passed")
    except Exception as e:
        log.error(f"❌ Alembic configuration validation failed: {e}")
        validation_passed = False
        all_issues.append(f"Alembic validation error: {e}")

    # Final validation result
    if validation_passed:
        log.info("🎉 Migration validation PASSED - Ready for migration!")
        return True
    else:
        log.error("❌ Migration validation FAILED - Fix issues before migration")

        if verbose:
            log.error("Summary of all issues found:")
            for i, issue in enumerate(all_issues, 1):
                log.error(f"  {i}. {issue}")

        if strict or any("error" in issue.lower() for issue in all_issues):
            raise MigrationValidationError(
                f"Migration validation failed with {len(all_issues)} issues. "
                f"Fix these issues before running migration."
            )

        return False


def _validate_alembic_config() -> list[str]:
    """
    Validate Alembic configuration and environment.

    Returns:
        List of configuration issues found
    """
    issues: list[str] = []

    # Check if alembic.ini exists
    alembic_ini = Path("alembic.ini")
    if not alembic_ini.exists():
        issues.append("alembic.ini file not found")

    # Check if alembic directory exists
    alembic_dir = Path("alembic")
    if not alembic_dir.exists():
        issues.append("alembic directory not found")
    else:
        # Check if env.py exists
        env_py = alembic_dir / "env.py"
        if not env_py.exists():
            issues.append("alembic/env.py file not found")

        # Check if versions directory exists
        versions_dir = alembic_dir / "versions"
        if not versions_dir.exists():
            issues.append("alembic/versions directory not found")

    # Check if we can import alembic
    try:
        import alembic

        log.debug(f"Alembic version: {alembic.__version__}")
    except ImportError:
        issues.append("Alembic is not installed or not accessible")

    return issues


def validate_database_connection() -> bool:
    """
    Validate database connection before migration.

    Returns:
        True if connection is successful, False otherwise
    """
    log.info("🔌 Validating database connection...")

    try:
        from global_config import global_config

        # Check if database URI is configured
        if not global_config.BACKEND_DB_URI:
            log.error("❌ Database URI not configured")
            return False

        # Try to create a connection
        from src.db.models import get_raw_engine

        engine = get_raw_engine()

        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")  # type: ignore
            if result.scalar() == 1:  # type: ignore
                log.info("✅ Database connection successful")
                return True
            else:
                log.error("❌ Database connection test failed")
                return False

    except Exception as e:
        log.error(f"❌ Database connection failed: {e}")
        return False


def quick_validation() -> bool:
    """
    Quick validation suitable for pre-commit hooks.

    Returns:
        True if basic validation passes, False otherwise
    """
    log.info("🚀 Running quick migration validation...")

    try:
        # Basic import validation
        if not validate_import_completeness():
            return False

        # Basic dependency validation (errors only)
        issues = validate_model_dependencies()
        critical_issues = [issue for issue in issues if issue.severity == "error"]

        if critical_issues:
            log.error(f"❌ Found {len(critical_issues)} critical issues")
            return False

        log.info("✅ Quick validation passed")
        return True

    except Exception as e:
        log.error(f"❌ Quick validation failed: {e}")
        return False


def migration_preflight_check() -> bool:
    """
    Complete pre-flight check before migration.

    Returns:
        True if all checks pass, False otherwise
    """
    log.info("🛫 Running migration pre-flight check...")

    checks = [
        ("Database Connection", validate_database_connection),
        (
            "Migration Readiness",
            lambda: validate_migration_readiness(strict=True, verbose=False),
        ),
    ]

    all_passed = True

    for check_name, check_func in checks:
        log.info(f"Checking {check_name}...")
        try:
            if not check_func():
                log.error(f"❌ {check_name} check failed")
                all_passed = False
            else:
                log.info(f"✅ {check_name} check passed")
        except Exception as e:
            log.error(f"❌ {check_name} check failed with error: {e}")
            all_passed = False

    if all_passed:
        log.info("🎉 All pre-flight checks passed - Clear for migration!")
    else:
        log.error("❌ Pre-flight checks failed - Fix issues before migration")

    return all_passed


if __name__ == "__main__":
    """Command line interface for migration validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate migration readiness")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick validation only"
    )
    parser.add_argument(
        "--preflight", action="store_true", help="Run full pre-flight check"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    try:
        if args.quick:
            success = quick_validation()
        elif args.preflight:
            success = migration_preflight_check()
        else:
            success = validate_migration_readiness(
                strict=args.strict, verbose=not args.quiet
            )

        sys.exit(0 if success else 1)

    except Exception as e:
        log.error(f"Validation failed with error: {e}")
        sys.exit(1)