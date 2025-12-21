"""add_referrals_to_profiles

Revision ID: 9b2d7c4a1e3f
Revises: 062573113f68
Create Date: 2025-12-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b2d7c4a1e3f"
down_revision: Union[str, Sequence[str], None] = "062573113f68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add referral columns to public.profiles (nullable for backwards compatibility)
    op.add_column(
        "profiles", sa.Column("referral_code", sa.String(), nullable=True), schema="public"
    )
    op.add_column(
        "profiles", sa.Column("referred_by_user_id", sa.UUID(), nullable=True), schema="public"
    )
    op.add_column(
        "profiles",
        sa.Column("referred_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )

    # Constraints and indexes
    op.create_unique_constraint(
        "profiles_referral_code_key", "profiles", ["referral_code"], schema="public"
    )
    op.create_foreign_key(
        "profiles_referred_by_user_id_fkey",
        "profiles",
        "profiles",
        ["referred_by_user_id"],
        ["user_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
        use_alter=True,
    )
    op.create_index(
        "idx_profiles_referral_code",
        "profiles",
        ["referral_code"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "idx_profiles_referred_by_user_id",
        "profiles",
        ["referred_by_user_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_profiles_referred_by_user_id", table_name="profiles", schema="public")
    op.drop_index("idx_profiles_referral_code", table_name="profiles", schema="public")
    op.drop_constraint(
        "profiles_referred_by_user_id_fkey", "profiles", type_="foreignkey", schema="public"
    )
    op.drop_constraint(
        "profiles_referral_code_key", "profiles", type_="unique", schema="public"
    )
    op.drop_column("profiles", "referred_at", schema="public")
    op.drop_column("profiles", "referred_by_user_id", schema="public")
    op.drop_column("profiles", "referral_code", schema="public")

