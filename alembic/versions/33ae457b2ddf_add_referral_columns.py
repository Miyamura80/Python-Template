"""Add referral columns

Revision ID: 33ae457b2ddf
Revises: 8b9c2e1f4c1c
Create Date: 2025-12-26 10:37:46.325765

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision: str = "33ae457b2ddf"
down_revision: Union[str, Sequence[str], None] = "8b9c2e1f4c1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define a minimal model for data migration
Base = declarative_base()


class Profile(Base):
    __tablename__ = "profiles"
    user_id = sa.Column(sa.UUID, primary_key=True)
    referral_code = sa.Column(sa.String)
    referral_count = sa.Column(sa.Integer)


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add columns as nullable first
    op.add_column("profiles", sa.Column("referral_code", sa.String(), nullable=True))
    op.add_column("profiles", sa.Column("referrer_id", sa.UUID(), nullable=True))
    op.add_column("profiles", sa.Column("referral_count", sa.Integer(), nullable=True))

    # 2. Backfill existing rows with 0 count, but keep referral_code null if desired.
    # User requested: "If the referral code is null, it just means that the user self signed up and we do not need to generate a default"
    # However, existing users might want to refer others.
    # But strictly following instructions: make it nullable, remove default generation.
    # I will set referral_count to 0 for existing rows so it is not null.

    bind = op.get_bind()
    session = Session(bind=bind)

    # Initialize referral_count to 0
    session.execute(sa.text("UPDATE profiles SET referral_count = 0"))
    session.commit()

    # 3. Alter columns
    # referral_code stays nullable=True
    # referral_count becomes nullable=False
    op.alter_column("profiles", "referral_count", nullable=False)

    # 4. Create unique constraint and index
    op.create_unique_constraint(
        "uq_profiles_referral_code", "profiles", ["referral_code"]
    )
    op.create_index("ix_profiles_referral_code", "profiles", ["referral_code"])

    # Add foreign key for referrer_id
    op.create_foreign_key(
        "fk_profiles_referrer_id", "profiles", "profiles", ["referrer_id"], ["user_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_profiles_referrer_id", "profiles", type_="foreignkey")
    op.drop_index("ix_profiles_referral_code", table_name="profiles")
    op.drop_constraint("uq_profiles_referral_code", "profiles", type_="unique")
    op.drop_column("profiles", "referral_count")
    op.drop_column("profiles", "referrer_id")
    op.drop_column("profiles", "referral_code")
