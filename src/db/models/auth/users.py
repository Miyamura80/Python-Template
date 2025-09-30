from typing import Any

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Text,
    JSON,
    SmallInteger,
    TIMESTAMP,
    UUID,
)

from src.db.models import Base


class User(Base):
    """
    A user is a person who has an account on the platform.
    This is a view on the auth.users table, which is considered readonly from the app side.
    Thus we don't manage it
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    instance_id = Column(UUID)  # noqa # type: ignore
    id = Column(UUID, primary_key=True)  # noqa # type: ignore
    aud = Column(String(255))  # noqa
    role = Column(String(255))  # noqa
    email = Column(String(255))  # noqa
    encrypted_password = Column(String(255))  # noqa
    email_confirmed_at = Column(TIMESTAMP(timezone=True))  # noqa
    invited_at = Column(TIMESTAMP(timezone=True))  # noqa
    confirmation_token = Column(String(255))  # noqa
    confirmation_sent_at = Column(TIMESTAMP(timezone=True))  # noqa
    recovery_token = Column(String(255))  # noqa
    recovery_sent_at = Column(TIMESTAMP(timezone=True))  # noqa
    email_change_token_new = Column(String(255))  # noqa
    email_change = Column(String(255))  # noqa
    email_change_sent_at = Column(TIMESTAMP(timezone=True))  # noqa
    last_sign_in_at = Column(TIMESTAMP(timezone=True))  # noqa
    raw_app_meta_data = Column(JSON)  # noqa
    raw_user_meta_data = Column(JSON)  # noqa
    is_super_admin = Column(Boolean)  # noqa
    created_at = Column(TIMESTAMP(timezone=True))  # noqa
    updated_at = Column(TIMESTAMP(timezone=True))  # noqa
    phone = Column(Text, unique=True)  # noqa
    phone_confirmed_at = Column(TIMESTAMP(timezone=True))  # noqa
    phone_change = Column(Text, server_default="")  # noqa
    phone_change_token = Column(String(255), server_default="")  # noqa
    phone_change_sent_at = Column(TIMESTAMP(timezone=True))  # noqa
    confirmed_at = Column(TIMESTAMP(timezone=True))  # noqa
    email_change_token_current = Column(String(255), server_default="")  # noqa
    email_change_confirm_status = Column(SmallInteger, server_default="0")  # noqa
    banned_until = Column(TIMESTAMP(timezone=True))  # noqa
    reauthentication_token = Column(String(255), server_default="")  # noqa
    reauthentication_sent_at = Column(TIMESTAMP(timezone=True))  # noqa
    is_sso_user = Column(Boolean, nullable=False, server_default="false")  # noqa
    deleted_at = Column(TIMESTAMP(timezone=True))  # noqa
    is_anonymous = Column(Boolean, nullable=False, server_default="false")  # noqa

    # This model represents a view, so we need to disable any write operations
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("This model is read-only")

    def save(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("This model is read-only")

    def delete(self, *args: Any, **kwargs: Any) -> None:  # noqa
        raise NotImplementedError("This model is read-only")

    @classmethod
    def create(cls, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("This model is read-only")
