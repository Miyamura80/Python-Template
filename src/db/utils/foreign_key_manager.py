"""
Foreign Key Management System

This module provides utilities for proper foreign key definition with automatic
use_alter detection to prevent circular dependency issues in migrations.
"""

from typing import Set, Optional, Any
from sqlalchemy import ForeignKeyConstraint, Index

from loguru import logger as log
from src.utils.logging_config import setup_logging
from .model_discovery import get_all_models

# Setup logging
setup_logging()


class ForeignKeyManager:
    """Manages foreign key relationships and automatically detects use_alter requirements."""

    def __init__(self):
        self.models = get_all_models()
        self.dependency_graph: dict[str, Set[str]] = {}
        self.circular_dependencies: Set[str] = set()
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build the dependency graph from current models."""
        log.debug("Building dependency graph for foreign key management")

        self.dependency_graph = {}

        for model_name, model_class in self.models.items():
            self.dependency_graph[model_name] = set()

            if not hasattr(model_class, "__table__"):
                continue

            # Analyze foreign key relationships
            for fk in model_class.__table__.foreign_keys:
                referenced_table = fk.column.table.name

                # Find the model that owns this table
                for other_model_name, other_model_class in self.models.items():
                    if (
                        hasattr(other_model_class, "__tablename__")
                        and other_model_class.__tablename__ == referenced_table
                    ):
                        self.dependency_graph[model_name].add(other_model_name)
                        break

        # Detect circular dependencies
        self._detect_circular_dependencies()

    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies in the model graph."""
        log.debug("Detecting circular dependencies")

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Find all models involved in cycles
        for model_name in self.models.keys():
            if model_name not in visited:
                if has_cycle(model_name):
                    # This path contains a cycle, mark all models in rec_stack
                    self.circular_dependencies.update(rec_stack)

        if self.circular_dependencies:
            log.warning(
                f"Detected circular dependencies involving: {self.circular_dependencies}"
            )

    def create_foreign_key_constraint(
        self,
        columns: list[str],
        referred_columns: list[str],
        referred_table: str,
        schema: str = "public",
        referred_schema: str = "public",
        name: Optional[str] = None,
        ondelete: Optional[str] = None,
        onupdate: Optional[str] = None,
        initially: Optional[str] = None,
        deferrable: Optional[bool] = None,
        match: Optional[str] = None,
    ) -> ForeignKeyConstraint:
        """
        Create a foreign key constraint with automatic use_alter detection.

        Args:
            columns: Local column names
            referred_columns: Referenced column names
            referred_table: Referenced table name
            schema: Local table schema (default: "public")
            referred_schema: Referenced table schema (default: "public")
            name: Constraint name (auto-generated if None)
            ondelete: ON DELETE action
            onupdate: ON UPDATE action
            initially: INITIALLY value for deferrable constraints
            deferrable: Whether constraint is deferrable
            match: MATCH type for foreign key

        Returns:
            ForeignKeyConstraint with appropriate use_alter setting
        """
        log.debug(
            f"Creating foreign key constraint to {referred_schema}.{referred_table}"
        )

        # Build the referred columns list with schema prefix
        referred_column_specs = [
            f"{referred_schema}.{referred_table}.{col}" for col in referred_columns
        ]

        # Determine if use_alter is needed
        use_alter = self._should_use_alter(referred_table)

        # Generate constraint name if not provided
        if name is None:
            name = f"fk_{schema}_{referred_table}_{columns[0]}"

        # Create the constraint
        constraint = ForeignKeyConstraint(
            columns=columns,
            refcolumns=referred_column_specs,
            name=name,
            ondelete=ondelete,
            onupdate=onupdate,
            initially=initially,
            deferrable=deferrable,
            match=match,
            use_alter=use_alter,
        )

        log.debug(f"Created foreign key constraint '{name}' with use_alter={use_alter}")
        return constraint

    def _should_use_alter(self, referred_table: str) -> bool:
        """
        Determine if a foreign key should use use_alter=True.

        Args:
            referred_table: Name of the referenced table

        Returns:
            True if use_alter should be used, False otherwise
        """
        # Find the model that owns the referred table
        referred_model = None
        for model_name, model_class in self.models.items():
            if (
                hasattr(model_class, "__tablename__")
                and model_class.__tablename__ == referred_table
            ):
                referred_model = model_name
                break

        if referred_model is None:
            log.warning(f"Referenced table {referred_table} not found in models")
            return False

        # Check if the referred model is involved in circular dependencies
        return referred_model in self.circular_dependencies

    def get_recommended_indexes(
        self, table_name: str, foreign_key_columns: list[str]
    ) -> list[Index]:
        """
        Get recommended indexes for foreign key columns.

        Args:
            table_name: Name of the table
            foreign_key_columns: List of foreign key column names

        Returns:
            List of recommended Index objects
        """
        indexes: list[Index] = []

        for column in foreign_key_columns:
            index_name = f"idx_{table_name}_{column}"
            index = Index(index_name, column)
            indexes.append(index)
            log.debug(f"Recommended index: {index_name}")

        return indexes

    def validate_foreign_key_setup(self, model_name: str) -> list[str]:
        """
        Validate foreign key setup for a specific model.

        Args:
            model_name: Name of the model to validate

        Returns:
            List of validation issues found
        """
        issues: list[str] = []

        if model_name not in self.models:
            issues.append(f"Model {model_name} not found")
            return issues

        model_class = self.models[model_name]

        if not hasattr(model_class, "__table__"):
            issues.append(f"Model {model_name} has no __table__ attribute")
            return issues

        # Check foreign key constraints
        for fk in model_class.__table__.foreign_keys:
            referenced_table = fk.column.table.name

            # Check if referenced table exists
            table_exists = any(
                hasattr(other_model, "__tablename__")
                and other_model.__tablename__ == referenced_table
                for other_model in self.models.values()
            )

            if not table_exists:
                issues.append(
                    f"Foreign key references non-existent table: {referenced_table}"
                )

            # Check schema prefix
            column_str = str(fk.column)
            if "." not in column_str:
                issues.append(f"Foreign key missing schema prefix: {column_str}")

        # Check use_alter for circular dependencies
        if model_name in self.circular_dependencies:
            if hasattr(model_class, "__table_args__"):
                table_args = model_class.__table_args__
                if isinstance(table_args, tuple):
                    use_alter_found = False
                    for constraint in table_args:  # type: ignore
                        if (
                            hasattr(constraint, "columns")  # type: ignore
                            and hasattr(constraint, "referred_table")  # type: ignore
                            and getattr(constraint, "use_alter", False)  # type: ignore
                        ):
                            use_alter_found = True
                            break

                    if not use_alter_found:
                        issues.append(
                            f"Model {model_name} in circular dependency should use use_alter=True"
                        )

        return issues

    def get_dependency_report(self) -> str:
        """
        Generate a report of model dependencies and circular dependencies.

        Returns:
            Formatted dependency report
        """
        report = "📊 Foreign Key Dependency Report\n\n"

        # Overall statistics
        total_models = len(self.models)
        total_dependencies = sum(len(deps) for deps in self.dependency_graph.values())
        circular_count = len(self.circular_dependencies)

        report += "📈 Statistics:\n"
        report += f"  • Total models: {total_models}\n"
        report += f"  • Total dependencies: {total_dependencies}\n"
        report += f"  • Models in circular dependencies: {circular_count}\n\n"

        # Circular dependencies
        if self.circular_dependencies:
            report += "🔄 Circular Dependencies:\n"
            for model in sorted(self.circular_dependencies):
                report += f"  • {model}\n"
            report += "\n"

        # Dependency graph
        report += "🔗 Dependency Graph:\n"
        for model_name, dependencies in sorted(self.dependency_graph.items()):
            if dependencies:
                deps_str = ", ".join(sorted(dependencies))
                report += f"  • {model_name} → {deps_str}\n"
            else:
                report += f"  • {model_name} (no dependencies)\n"

        return report


def create_foreign_key_constraint(
    columns: list[str],
    referred_columns: list[str],
    referred_table: str,
    schema: str = "public",
    referred_schema: str = "public",
    **kwargs: Any,
) -> ForeignKeyConstraint:
    """
    Convenience function to create a foreign key constraint with automatic use_alter detection.

    Args:
        columns: Local column names
        referred_columns: Referenced column names
        referred_table: Referenced table name
        schema: Local table schema (default: "public")
        referred_schema: Referenced table schema (default: "public")
        **kwargs: Additional arguments for ForeignKeyConstraint

    Returns:
        ForeignKeyConstraint with appropriate use_alter setting
    """
    manager = ForeignKeyManager()
    return manager.create_foreign_key_constraint(
        columns=columns,
        referred_columns=referred_columns,
        referred_table=referred_table,
        schema=schema,
        referred_schema=referred_schema,
        **kwargs,
    )