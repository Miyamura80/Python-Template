"""add_user_subscriptions_table_and_missing_foreign_keys

Revision ID: f148a5bbb1f2
Revises: 2615f2e2da9e
Create Date: 2025-11-26 20:57:14.031072

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f148a5bbb1f2"
down_revision: Union[str, Sequence[str], None] = "2615f2e2da9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trial_start_date", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("subscription_start_date", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("subscription_end_date", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("subscription_tier", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("renewal_date", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "payment_failure_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_payment_failure", postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )

    # Add foreign key constraint for user_subscriptions.user_id
    op.create_foreign_key(
        "user_subscriptions_user_id_fkey",
        "user_subscriptions",
        "profiles",
        ["user_id"],
        ["user_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
    )

    # Add missing foreign key constraint for organizations.owner_user_id
    # This uses use_alter=True, so it needs to be added separately
    op.create_foreign_key(
        "organizations_owner_user_id_fkey",
        "organizations",
        "profiles",
        ["owner_user_id"],
        ["user_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )

    # Add missing foreign key constraint for profiles.organization_id
    # This uses use_alter=True, so it needs to be added separately
    op.create_foreign_key(
        "profiles_organization_id_fkey",
        "profiles",
        "organizations",
        ["organization_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraints
    op.drop_constraint(
        "profiles_organization_id_fkey", "profiles", schema="public", type_="foreignkey"
    )
    op.drop_constraint(
        "organizations_owner_user_id_fkey",
        "organizations",
        schema="public",
        type_="foreignkey",
    )
    op.drop_constraint(
        "user_subscriptions_user_id_fkey",
        "user_subscriptions",
        schema="public",
        type_="foreignkey",
    )

    # Drop user_subscriptions table
    op.drop_table("user_subscriptions", schema="public")
