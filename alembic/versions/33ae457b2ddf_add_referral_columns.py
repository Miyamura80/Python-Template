"""Add referral columns

Revision ID: 33ae457b2ddf
Revises: 8b9c2e1f4c1c
Create Date: 2025-12-26 10:37:46.325765

"""
from typing import Sequence, Union
import string
import secrets

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision: str = '33ae457b2ddf'
down_revision: Union[str, Sequence[str], None] = '8b9c2e1f4c1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define a minimal model for data migration
Base = declarative_base()

class Profile(Base):
    __tablename__ = 'profiles'
    user_id = sa.Column(sa.UUID, primary_key=True)
    referral_code = sa.Column(sa.String)
    referral_count = sa.Column(sa.Integer)

def generate_referral_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add columns as nullable first
    op.add_column('profiles', sa.Column('referral_code', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('referrer_id', sa.UUID(), nullable=True))
    op.add_column('profiles', sa.Column('referral_count', sa.Integer(), nullable=True))

    # 2. Backfill existing rows
    bind = op.get_bind()
    session = Session(bind=bind)

    # Check if there are any profiles
    # Note: We use execute directly to avoid issues with model definitions
    profiles_result = session.execute(sa.text("SELECT user_id FROM profiles"))
    profiles = profiles_result.fetchall()

    for row in profiles:
        user_id = row[0]
        # Generate unique code (simplified check for migration script)
        code = generate_referral_code()

        # Update each row
        session.execute(
            sa.text("UPDATE profiles SET referral_code = :code, referral_count = 0 WHERE user_id = :uid"),
            {"code": code, "uid": user_id}
        )

    session.commit()

    # 3. Alter columns to be non-nullable
    op.alter_column('profiles', 'referral_code', nullable=False)
    op.alter_column('profiles', 'referral_count', nullable=False)

    # 4. Create unique constraint and index
    op.create_unique_constraint("uq_profiles_referral_code", "profiles", ["referral_code"])
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
    op.drop_column('profiles', 'referral_count')
    op.drop_column('profiles', 'referrer_id')
    op.drop_column('profiles', 'referral_code')
