"""add referrals table

Revision ID: a1b2c3d4e5f6
Revises: 8b9c2e1f4c1c
Create Date: 2025-12-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8b9c2e1f4c1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the ReferralStatus enum type
    referral_status_enum = sa.Enum(
        "PENDING", "COMPLETED", "EXPIRED", name="referralstatus"
    )
    referral_status_enum.create(op.get_bind(), checkfirst=True)

    # Create the referrals table
    op.create_table(
        "referrals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("referrer_user_id", sa.UUID(), nullable=False),
        sa.Column("referred_user_id", sa.UUID(), nullable=True),
        sa.Column("referral_code", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "COMPLETED", "EXPIRED", name="referralstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "credits_awarded_to_referrer",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "credits_awarded_to_referred",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["referrer_user_id"],
            ["public.profiles.user_id"],
            name="referrals_referrer_user_id_fkey",
            ondelete="CASCADE",
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ["referred_user_id"],
            ["public.profiles.user_id"],
            name="referrals_referred_user_id_fkey",
            ondelete="SET NULL",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_code", name="uq_referrals_referral_code"),
        schema="public",
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_referrals_referrer_user_id",
        "referrals",
        ["referrer_user_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "idx_referrals_referred_user_id",
        "referrals",
        ["referred_user_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "idx_referrals_referral_code",
        "referrals",
        ["referral_code"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(
        "idx_referrals_referral_code", table_name="referrals", schema="public"
    )
    op.drop_index(
        "idx_referrals_referred_user_id", table_name="referrals", schema="public"
    )
    op.drop_index(
        "idx_referrals_referrer_user_id", table_name="referrals", schema="public"
    )

    # Drop the table
    op.drop_table("referrals", schema="public")

    # Drop the enum type
    sa.Enum(name="referralstatus").drop(op.get_bind(), checkfirst=True)
