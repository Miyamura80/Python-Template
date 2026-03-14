import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.schema import Table

from src.api.auth.api_key_auth import (
    create_api_key,
    get_current_user_from_api_key_header,
    hash_api_key,
)
from src.db.database import create_db_session
from src.db.models.public.api_keys import APIKey
from tests.test_template import TestTemplate


def build_request_with_api_key(api_key: str) -> Request:
    """
    Create a minimal Starlette request with the API key header set.
    """

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-api-key", api_key.encode())],
        "scheme": "http",
        "client": ("testclient", 5000),
        "server": ("testserver", 80),
    }
    return Request(scope, receive)


class TestAPIKeyAuth(TestTemplate):
    """Unit tests for API key authentication."""

    @pytest.fixture()
    def db_session(self):
        session = create_db_session()
        # Ensure the api_keys table exists for tests
        table: Table = APIKey.__table__  # type: ignore[attr-defined]
        table.create(bind=session.get_bind(), checkfirst=True)
        yield session
        session.query(APIKey).delete()
        session.commit()
        session.close()

    @pytest.mark.asyncio
    async def test_api_key_authentication_succeeds(self, db_session):
        user_id = str(uuid.uuid4())
        raw_key = create_api_key(db_session, user_id=user_id, name="test-key")

        request = build_request_with_api_key(raw_key)
        authenticated_user_id = await get_current_user_from_api_key_header(
            request, db_session
        )

        assert authenticated_user_id == user_id

    @pytest.mark.asyncio
    async def test_revoked_api_key_is_rejected(self, db_session):
        user_id = str(uuid.uuid4())
        raw_key = create_api_key(db_session, user_id=user_id)

        api_key_record = (
            db_session.query(APIKey)
            .filter(APIKey.key_hash == hash_api_key(raw_key))
            .first()
        )
        api_key_record.revoked = True
        assert api_key_record.revoked is True
        db_session.commit()

        request = build_request_with_api_key(raw_key)

        with pytest.raises(HTTPException) as excinfo:
            await get_current_user_from_api_key_header(request, db_session)

        assert isinstance(excinfo.value, HTTPException)
        assert excinfo.value.status_code == 401
        assert "revoked" in excinfo.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expired_api_key_is_rejected(self, db_session):
        user_id = str(uuid.uuid4())
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        raw_key = create_api_key(
            db_session, user_id=user_id, name="expired-key", expires_at=expired_at
        )

        request = build_request_with_api_key(raw_key)

        with pytest.raises(HTTPException) as excinfo:
            await get_current_user_from_api_key_header(request, db_session)

        assert isinstance(excinfo.value, HTTPException)
        assert excinfo.value.status_code == 401
        assert "expired" in excinfo.value.detail.lower()
