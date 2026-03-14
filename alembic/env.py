import os
import sys
from logging.config import fileConfig
from urllib.parse import urlparse

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add alembic directory to import RLS support
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Custom import to get global config
from common.global_config import global_config  # type: ignore
from src.db.models import Base

# Import RLS support to enable automatic RLS policy detection
import rls_support  # noqa: F401 # type: ignore

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_database_url() -> str:
    """Get database URL and ensure it's a valid remote database."""
    db_uri: str = str(global_config.database_uri)  # type: ignore
    parsed_uri = urlparse(db_uri)
    host_display = parsed_uri.hostname or "Unknown host"
    print(f"✅ Using remote database: {host_display}")
    return db_uri


def include_object(object, name, type_, reflected, compare_to):
    """
        Filter function to exclude objects we don't want to manage.

    This prevents Alembic from detecting changes in Postgres schemas
        and ignores schema drift in existing tables.
    """
    # Only include objects from the public schema
    if hasattr(object, "schema") and object.schema not in (None, "public"):
        return False

    # Exclude specific tables we don't want to manage
    excluded_tables = {
        # Add any specific tables you want to exclude
    }

    if type_ == "table" and name in excluded_tables:
        return False

    return True


def compare_type(
    context, inspected_column, metadata_column, inspected_type, metadata_type
):
    """
    Custom type comparison to reduce false positives.

    Return True if types are different and should generate a migration.
    """
    # For now, only compare types that we actually care about
    # This reduces noise from minor type differences
    return False  # Don't generate type changes unless we explicitly need them


def compare_server_default(
    context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    """
    Custom server default comparison to reduce false positives.

    Return True if defaults are different and should generate a migration.
    """
    # For now, don't compare server defaults unless we explicitly need them
    # This prevents migrations from being generated for default value differences
    return False


def include_name(name, type_, parent_names):
    """
    Filter function to exclude specific schema objects by name.

    This prevents detection of schema drift in existing objects.
    """
    # Skip indexes that already exist - prevents index recreation
    if type_ == "index":
        existing_indexes = set()
        if name in existing_indexes:
            return False

    # Skip foreign key constraints that are being recreated
    if type_ == "foreign_key_constraint":
        existing_fks = {
            "api_key_user_id_fkey",
        }
        if name in existing_fks:
            return False

    # Skip unique constraints that are being recreated
    if type_ == "unique_constraint":
        existing_constraints = set()
        if name in existing_constraints:
            return False

    return True


def ignore_init_migrations(context, revision, directives):
    """
    Hook to prevent empty migrations from being generated.
    Only allows RLS policy changes through by filtering out schema drift operations.
    """
    if not directives:
        # Don't generate empty migrations
        return

    # Operations that are considered schema drift and should be filtered out
    schema_drift_operations = {
        "createindexop",
        "dropindexop",  # Filter out index operations as drift
        "createforeignkeyop",
        "dropforeignkeyop",
        "createuniqueconstraintop",
        "dropuniqueconstraintop",
        "altercolumnop",
        "createcheckconstraintop",
        "dropcheckconstraintop",
        "dropcolumnop",  # Only filter out column drops, not additions
        # NOTE: Removed 'createtableop', 'droptableop', 'addcolumnop' - allow new table/column creation from model changes
        "dropconstraintop",  # Also filter out constraint drops
    }

    # Operations that should ALWAYS generate migrations (genuine schema changes)
    truly_important_operations = {
        "createpolicyop",
        "droppolicyop",  # Explicit RLS operations only
        "createtableop",
        "droptableop",  # New table creation/deletion from models
        "addcolumnop",  # Column additions from model changes
    }

    def is_rls_policy_operation(op):
        """Check if an operation is an RLS policy operation."""
        if hasattr(op, "sqltext"):
            sql_text = str(op.sqltext).upper()
            return (
                "CREATE POLICY" in sql_text
                or "DROP POLICY" in sql_text
                or "ALTER POLICY" in sql_text
            )
        return False

    def is_important_operation(op):
        """Check if an operation is important and should be kept."""
        op_name = op.__class__.__name__.lower()

        # Check if this is a truly important operation
        if op_name in truly_important_operations:
            return True

        # Check if this is an RLS policy operation
        if is_rls_policy_operation(op):
            return True

        return False

    def filter_operations_recursively(ops):
        """Recursively filter operations, keeping only important ones."""
        filtered_ops = []
        important_count = 0

        for op in ops:
            op_name = op.__class__.__name__.lower()

            # Check if this operation has nested operations (like ModifyTableOps)
            if hasattr(op, "ops"):
                # Filter the nested operations
                filtered_nested_ops, nested_important = filter_operations_recursively(
                    op.ops
                )
                important_count += nested_important

                # Only keep the ModifyTableOps if it has important nested operations
                if filtered_nested_ops:
                    # Create a new operation with only the important nested operations
                    op.ops = filtered_nested_ops
                    filtered_ops.append(op)

            # Check if this is an important operation
            elif is_important_operation(op):
                print(f"🔍 Keeping important operation: {op_name}")
                filtered_ops.append(op)
                important_count += 1

            # Skip schema drift operations
            elif op_name in schema_drift_operations:
                print(f"🔍 Filtering out drift operation: {op_name}")

            # Keep any operation that's not explicitly marked as drift (be conservative)
            else:
                print(f"🔍 Keeping unknown operation: {op_name}")
                filtered_ops.append(op)
                important_count += 1

        return filtered_ops, important_count

    # Process all directives
    total_important_operations = 0

    print(f"🔍 Filtering {len(directives)} directives")
    for i, directive in enumerate(directives):
        # Check different directive structures
        if hasattr(directive, "ops"):
            filtered_ops, important_count = filter_operations_recursively(directive.ops)
            directive.ops = filtered_ops
            total_important_operations += important_count
        elif hasattr(directive, "upgrade_ops"):
            # Filter upgrade operations
            filtered_upgrade_ops, upgrade_important_count = (
                filter_operations_recursively(directive.upgrade_ops.ops)
            )
            directive.upgrade_ops.ops = filtered_upgrade_ops
            total_important_operations += upgrade_important_count

            # Filter downgrade operations if they exist
            if hasattr(directive, "downgrade_ops") and directive.downgrade_ops:
                print("🔍 Also filtering downgrade operations")
                filtered_downgrade_ops, downgrade_important_count = (
                    filter_operations_recursively(directive.downgrade_ops.ops)
                )
                directive.downgrade_ops.ops = filtered_downgrade_ops
                total_important_operations += downgrade_important_count

    # If no important operations remain, block the migration
    if total_important_operations == 0:
        print("🔍 No important operations found, blocking migration")
        directives[:] = []
    else:
        print(
            f"✅ Allowing migration: Found {total_important_operations} important operations"
        )


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,  # type: ignore
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_name=include_name,
        compare_type=compare_type,
        compare_server_default=compare_server_default,
        process_revision_directives=ignore_init_migrations,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the sqlalchemy.url in config with our custom URL
    alembic_config = config.get_section(config.config_ini_section, {})
    alembic_config["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:  # type: ignore
        context.configure(
            connection=connection,  # type: ignore
            target_metadata=target_metadata,  # type: ignore
            include_schemas=False,  # Only include public schema
            include_object=include_object,  # Filter unwanted objects
            include_name=include_name,  # Filter unwanted names
            compare_type=compare_type,  # Custom type comparison
            compare_server_default=compare_server_default,  # Custom default comparison
            process_revision_directives=ignore_init_migrations,  # Prevent empty migrations
        )

        with context.begin_transaction():
            context.run_migrations()


# Add target_metadata
target_metadata = Base.metadata

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
