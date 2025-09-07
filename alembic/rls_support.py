"""
RLS (Row-Level Security) support for Alembic migrations.

This module provides functionality to automatically detect and create
RLS policies defined in SQLAlchemy models during migrations.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection
from alembic.autogenerate import comparators
from alembic.operations.ops import ExecuteSQLOp


class ReversibleExecuteSQLOp(ExecuteSQLOp):
    """A reversible ExecuteSQLOp that can provide downgrade operations."""

    def __init__(self, sqltext, reverse_sql=None, **kwargs):
        super().__init__(sqltext, **kwargs)
        self.reverse_sql = reverse_sql

    def reverse(self):
        if self.reverse_sql:
            return ReversibleExecuteSQLOp(self.reverse_sql)
        else:
            # Return a no-op SQL statement that won't fail
            return ReversibleExecuteSQLOp("SELECT 1; -- No reverse operation available")


# Use simple SQL execution approach instead of custom operations


def get_existing_policies(
    connection: Connection, schema: str, table_name: str
) -> set[str]:
    """
    Query the database to get existing RLS policies for a table.

    Args:
        connection: Database connection
        schema: Schema name
        table_name: Table name

    Returns:
        Set of existing policy names
    """
    try:
        query = text("""
            SELECT policyname 
            FROM pg_policies 
            WHERE schemaname = :schema AND tablename = :table_name
        """)
        result = connection.execute(query, {"schema": schema, "table_name": table_name})
        return {row[0] for row in result}
    except Exception:
        # If we can't query policies (e.g., insufficient permissions), return empty set
        return set()


def get_table_rls_enabled(connection: Connection, schema: str, table_name: str) -> bool:
    """
    Check if RLS is enabled for a table.

    Args:
        connection: Database connection
        schema: Schema name
        table_name: Table name

    Returns:
        True if RLS is enabled, False otherwise
    """
    try:
        query = text("""
            SELECT c.relrowsecurity 
            FROM pg_class c 
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = :schema AND c.relname = :table_name
        """)
        result = connection.execute(query, {"schema": schema, "table_name": table_name})
        row = result.fetchone()
        return bool(row[0]) if row else False
    except Exception:
        return False


@comparators.dispatch_for("table")
def compare_rls_policies(
    autogen_context, modify_ops, schemaname, tablename, conn_table, metadata_table
):
    """
    Compare RLS policies defined in models with existing database policies.

    This function is called during autogeneration to detect RLS policy changes.
    """
    # Get model policies from table info (transferred from model class)
    model_policies = metadata_table.info.get("rls_policies", [])

    # Debug logging
    print(
        f"🔍 RLS comparison for {schemaname}.{tablename}: found {len(model_policies)} model policies"
    )

    if not model_policies:
        return

    # Get table info
    schema = schemaname or "public"
    table_name = tablename

    # Get existing policies from database
    connection = autogen_context.connection
    if connection is None:
        print("❌ No database connection available for RLS comparison")
        return
    existing_policies = get_existing_policies(connection, schema, table_name)
    rls_enabled = get_table_rls_enabled(connection, schema, table_name)

    print(f"📊 Existing policies for {schema}.{table_name}: {existing_policies}")
    print(f"🔒 RLS enabled: {rls_enabled}")

    # Build SQL operations
    sql_statements = []

    # Enable RLS if not already enabled and we have policies
    if not rls_enabled and model_policies:
        sql_statements.append(
            f"ALTER TABLE {schema}.{table_name} ENABLE ROW LEVEL SECURITY;"
        )

    # Check each model policy
    for policy_name, policy_config in model_policies.items():
        print(f"🔍 Checking policy: {policy_name}")

        if policy_name not in existing_policies:
            print(f"✨ Creating new policy: {policy_name}")
            # Policy doesn't exist, create it
            using_clause = policy_config["using"]
            check_clause = policy_config.get("check")
            permissive = policy_config.get("permissive", True)
            permissive_str = "PERMISSIVE" if permissive else "RESTRICTIVE"

            # Get policy command (defaults to SELECT if not specified)
            command = policy_config.get("command", "SELECT")

            # Build the CREATE POLICY statement
            policy_sql = f"CREATE POLICY {policy_name} ON {schema}.{table_name}\n"
            policy_sql += f"                AS {permissive_str}\n"
            policy_sql += f"                FOR {command}\n"
            policy_sql += f"                USING ({using_clause})"

            # Add CHECK clause for INSERT/UPDATE policies if specified
            if check_clause and command.upper() in ("INSERT", "UPDATE", "ALL"):
                policy_sql += f"\n                WITH CHECK ({check_clause})"

            policy_sql += ";"
            sql_statements.append(policy_sql)
        else:
            print(f"⏭️  Policy {policy_name} already exists, skipping")

    # If we have SQL statements to execute, add them to the migration
    if sql_statements:
        print("📝 Adding RLS operations to migration")

        # Combine all SQL statements into a single operation
        combined_sql = "\n".join(sql_statements)
        print(f"📝 Combined SQL:\n{combined_sql}")

        # Generate reverse SQL to drop the policies we're creating
        reverse_statements = []
        for policy_name, policy_config in model_policies.items():
            if policy_name not in existing_policies:
                reverse_statements.append(
                    f"DROP POLICY IF EXISTS {policy_name} ON {schema}.{table_name};"
                )

        reverse_sql = (
            "\n".join(reverse_statements)
            if reverse_statements
            else "-- No RLS policies to drop"
        )
        print(f"📝 Reverse SQL:\n{reverse_sql}")

        # Add reversible SQL operation to the migration
        modify_ops.ops.append(
            ReversibleExecuteSQLOp(sqltext=combined_sql, reverse_sql=reverse_sql)
        )
    else:
        print(f"ℹ️  No RLS changes needed for {schema}.{table_name}")