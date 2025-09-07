"""
Dependency Validation System

This module provides functionality to validate model dependencies, detect circular
dependencies, and identify foreign key issues before they cause migration problems.
"""

from typing import Set, Optional
from dataclasses import dataclass
from collections import defaultdict, deque

from loguru import logger as log
from src.utils.logging_config import setup_logging
from .model_discovery import get_all_models, get_model_dependencies

# Setup logging
setup_logging()


class DependencyValidationError(Exception):
    """Exception raised when dependency validation fails."""

    pass


@dataclass
class DependencyIssue:
    """Represents a dependency issue found during validation."""

    issue_type: str
    model_name: str
    description: str
    severity: str  # 'error', 'warning', 'info'
    suggestion: Optional[str] = None


class DependencyValidator:
    """Validates model dependencies and detects issues."""

    def __init__(self):
        self.models = get_all_models()
        self.dependencies = get_model_dependencies()
        self.issues: list[DependencyIssue] = []

    def validate_all(self) -> list[DependencyIssue]:
        """
        Run all validation checks and return list of issues found.

        Returns:
            List of dependency issues found
        """
        log.info("Starting comprehensive dependency validation")

        self.issues = []

        # Run all validation checks
        self._check_circular_dependencies()
        self._check_missing_foreign_key_targets()
        self._check_use_alter_requirements()
        self._check_schema_consistency()
        self._check_model_completeness()

        log.info(f"Dependency validation completed. Found {len(self.issues)} issues")
        return self.issues

    def _check_circular_dependencies(self) -> None:
        """Check for circular dependencies in model relationships."""
        log.debug("Checking for circular dependencies")

        # Use topological sort to detect cycles
        in_degree: defaultdict[str, int] = defaultdict(int)

        # Calculate in-degrees
        for _model, deps in self.dependencies.items():
            for dep in deps:
                in_degree[dep] += 1

        # Find nodes with no incoming edges
        queue = deque([model for model in self.models.keys() if in_degree[model] == 0])
        processed: Set[str] = set()

        while queue:
            current = queue.popleft()
            processed.add(current)

            # Process all dependencies of current model
            for dep in self.dependencies.get(current, set()):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        # If we couldn't process all models, there's a cycle
        unprocessed = set(self.models.keys()) - processed
        if unprocessed:
            # Find the actual cycles
            cycles = self._find_cycles(unprocessed)
            for cycle in cycles:
                # Check if this cycle is properly handled with use_alter=True
                is_properly_handled = self._is_cycle_properly_handled(cycle)

                if is_properly_handled:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="circular_dependency_handled",
                            model_name=" -> ".join(cycle),
                            description=f"Circular dependency detected but properly handled: {' -> '.join(cycle)}",
                            severity="info",
                            suggestion="Circular dependency is correctly handled with use_alter=True",
                        )
                    )
                else:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="circular_dependency",
                            model_name=" -> ".join(cycle),
                            description=f"Circular dependency detected: {' -> '.join(cycle)}",
                            severity="error",
                            suggestion="Consider using use_alter=True on one of the foreign keys in the cycle",
                        )
                    )

    def _find_cycles(self, models: Set[str]) -> list[list[str]]:
        """Find actual cycles in the dependency graph."""
        cycles: list[list[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for dep in self.dependencies.get(node, set()):
                if dep in models:  # Only consider unprocessed models
                    dfs(dep, path + [node])

            rec_stack.remove(node)

        for model in models:
            if model not in visited:
                dfs(model, [])

        return cycles

    def _is_cycle_properly_handled(self, cycle: list[str]) -> bool:
        """
        Check if a circular dependency cycle is properly handled with use_alter=True.

        Args:
            cycle: List of model names in the circular dependency

        Returns:
            True if the cycle is properly handled, False otherwise
        """
        models_in_cycle = set(cycle)

        # Check if at least one model in the cycle uses use_alter=True
        for model_name in models_in_cycle:
            if model_name not in self.models:
                continue

            model_class = self.models[model_name]
            if not hasattr(model_class, "__table_args__"):
                continue

            table_args = model_class.__table_args__
            if not isinstance(table_args, tuple):
                continue

            # Check foreign key constraints for use_alter=True
            for constraint in table_args:  # type: ignore
                if (
                    hasattr(constraint, "columns")  # type: ignore
                    and hasattr(constraint, "referred_table")  # type: ignore
                ):
                    # This is a foreign key constraint
                    if getattr(constraint, "use_alter", False):  # type: ignore
                        # Found at least one use_alter=True, cycle is properly handled
                        return True

        return False

    def _check_missing_foreign_key_targets(self) -> None:
        """Check for foreign keys that reference non-existent models."""
        log.debug("Checking for missing foreign key targets")

        for model_name, model_class in self.models.items():
            if not hasattr(model_class, "__table__"):
                continue

            for fk in model_class.__table__.foreign_keys:
                referenced_table = fk.column.table.name

                # Check if referenced table exists in our models
                table_exists = any(
                    hasattr(other_model, "__tablename__")
                    and other_model.__tablename__ == referenced_table
                    for other_model in self.models.values()
                )

                if not table_exists:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="missing_foreign_key_target",
                            model_name=model_name,
                            description=f"Foreign key references non-existent table: {referenced_table}",
                            severity="error",
                            suggestion="Ensure the referenced model is imported and has correct __tablename__",
                        )
                    )

    def _check_use_alter_requirements(self) -> None:
        """Check if foreign keys in circular dependencies use use_alter=True."""
        log.debug("Checking use_alter requirements")

        # First identify which models are in circular dependencies
        circular_models: Set[str] = set()
        for issue in self.issues:
            if issue.issue_type == "circular_dependency":
                # Parse the cycle to get individual models
                cycle_parts = issue.model_name.split(" -> ")
                circular_models.update(cycle_parts)

        # Check foreign keys in circular dependency models
        for model_name in circular_models:
            if model_name not in self.models:
                continue

            model_class = self.models[model_name]
            if not hasattr(model_class, "__table_args__"):
                continue

            table_args: tuple[str, ...] = model_class.__table_args__
            if not isinstance(table_args, tuple):  # type: ignore
                continue

            # Check foreign key constraints
            for constraint in table_args:
                if hasattr(constraint, "columns") and hasattr(
                    constraint, "referred_table"
                ):
                    # This is a foreign key constraint
                    if not getattr(constraint, "use_alter", False):
                        self.issues.append(
                            DependencyIssue(
                                issue_type="missing_use_alter",
                                model_name=model_name,
                                description="Foreign key constraint should use use_alter=True due to circular dependency",
                                severity="warning",
                                suggestion="Add use_alter=True to the ForeignKeyConstraint",
                            )
                        )

    def _check_schema_consistency(self) -> None:
        """Check for schema consistency in foreign key references."""
        log.debug("Checking schema consistency")

        for model_name, model_class in self.models.items():
            if not hasattr(model_class, "__table__"):
                continue

            for fk in model_class.__table__.foreign_keys:
                column_str = str(fk.column)

                # Check if schema prefix is used
                if "." not in column_str:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="missing_schema_prefix",
                            model_name=model_name,
                            description=f"Foreign key reference missing schema prefix: {column_str}",
                            severity="warning",
                            suggestion="Use explicit schema prefix (e.g., 'public.table_name.column_name')",
                        )
                    )

    def _check_model_completeness(self) -> None:
        """Check if all models have required attributes."""
        log.debug("Checking model completeness")

        for model_name, model_class in self.models.items():
            # Check required attributes
            required_attrs = ["__tablename__", "__table__"]
            for attr in required_attrs:
                if not hasattr(model_class, attr):
                    self.issues.append(
                        DependencyIssue(
                            issue_type="incomplete_model",
                            model_name=model_name,
                            description=f"Model missing required attribute: {attr}",
                            severity="error",
                            suggestion=f"Add {attr} to the model definition",
                        )
                    )

            # Check for proper timestamps
            if hasattr(model_class, "__table__"):
                columns = [col.name for col in model_class.__table__.columns]
                if "created_at" not in columns:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="missing_timestamp",
                            model_name=model_name,
                            description="Model missing created_at timestamp",
                            severity="warning",
                            suggestion="Add created_at column with proper timezone handling",
                        )
                    )
                if "updated_at" not in columns:
                    self.issues.append(
                        DependencyIssue(
                            issue_type="missing_timestamp",
                            model_name=model_name,
                            description="Model missing updated_at timestamp",
                            severity="warning",
                            suggestion="Add updated_at column with proper timezone handling",
                        )
                    )


def validate_model_dependencies() -> list[DependencyIssue]:
    """
    Convenience function to validate all model dependencies.

    Returns:
        List of dependency issues found

    Raises:
        DependencyValidationError: If critical issues are found
    """
    validator = DependencyValidator()
    issues = validator.validate_all()

    # Check for critical errors
    critical_issues = [issue for issue in issues if issue.severity == "error"]
    if critical_issues:
        error_msg = f"Found {len(critical_issues)} critical dependency issues:\n"
        for issue in critical_issues:
            error_msg += f"  - {issue.model_name}: {issue.description}\n"
        raise DependencyValidationError(error_msg)

    return issues


def format_validation_report(issues: list[DependencyIssue]) -> str:
    """
    Format validation issues into a readable report.

    Args:
        issues: List of dependency issues

    Returns:
        Formatted report string
    """
    if not issues:
        return "✅ No dependency issues found!"

    report = f"🔍 Dependency Validation Report - {len(issues)} issues found\n\n"

    # Group issues by severity
    by_severity: defaultdict[str, list[DependencyIssue]] = defaultdict(list)
    for issue in issues:
        by_severity[issue.severity].append(issue)

    # Report by severity
    for severity in ["error", "warning", "info"]:
        if severity not in by_severity:
            continue

        severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[severity]
        report += f"{severity_icon} {severity.upper()} Issues ({len(by_severity[severity])})\n"

        for issue in by_severity[severity]:
            report += f"  • {issue.model_name}: {issue.description}\n"
            if issue.suggestion:
                report += f"    💡 Suggestion: {issue.suggestion}\n"

        report += "\n"

    return report