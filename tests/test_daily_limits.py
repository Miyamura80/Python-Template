import uuid

from typing import Any, cast

import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.api import limits as daily_limits
from tests.test_template import TestTemplate


class TestDailyLimits(TestTemplate):
    """Unit tests for tier-aware daily limit enforcement."""

    def test_allow_within_limit(self, monkeypatch):
        """Should allow requests that are under the configured limit."""
        db_stub = cast(Session, None)
        monkeypatch.setattr(
            daily_limits, "_resolve_tier_for_user", lambda db, user_uuid: "free_tier"
        )
        monkeypatch.setattr(
            daily_limits, "_count_today_user_messages", lambda db, user_uuid: 3
        )

        status_snapshot = daily_limits.ensure_daily_limit(
            db=db_stub,
            user_uuid=uuid.uuid4(),
            limit_name=daily_limits.DEFAULT_LIMIT_NAME,
        )

        assert status_snapshot.is_within_limit
        assert status_snapshot.limit_value == 5
        assert status_snapshot.used_today == 3
        assert status_snapshot.remaining == 2

    def test_exceeding_limit_returns_status_without_enforcement(self, monkeypatch):
        """Should warn but not raise when over limit unless enforcement is enabled."""
        db_stub = cast(Session, None)
        monkeypatch.setattr(
            daily_limits, "_resolve_tier_for_user", lambda db, user_uuid: "plus_tier"
        )
        monkeypatch.setattr(
            daily_limits, "_count_today_user_messages", lambda db, user_uuid: 30
        )

        status_snapshot = daily_limits.ensure_daily_limit(
            db=db_stub,
            user_uuid=uuid.uuid4(),
            limit_name=daily_limits.DEFAULT_LIMIT_NAME,
        )

        assert not status_snapshot.is_within_limit
        assert status_snapshot.limit_value == 25
        assert status_snapshot.used_today == 30
        assert status_snapshot.remaining == 0
        detail = status_snapshot.to_error_detail()
        assert detail["code"] == "daily_limit_exceeded"
        detail_message = cast(str, detail["message"])
        assert "limit reached" in detail_message.lower()

    def test_exceeding_limit_can_be_enforced(self, monkeypatch):
        """Should still allow enforcement to raise 402 when explicitly requested."""
        db_stub = cast(Session, None)
        monkeypatch.setattr(
            daily_limits, "_resolve_tier_for_user", lambda db, user_uuid: "plus_tier"
        )
        monkeypatch.setattr(
            daily_limits, "_count_today_user_messages", lambda db, user_uuid: 30
        )

        with pytest.raises(HTTPException) as exc_info:
            daily_limits.ensure_daily_limit(
                db=db_stub,
                user_uuid=uuid.uuid4(),
                limit_name=daily_limits.DEFAULT_LIMIT_NAME,
                enforce=True,
            )

        error = cast(HTTPException, exc_info.value)
        assert error.status_code == status.HTTP_402_PAYMENT_REQUIRED
        detail = cast(dict[str, Any], error.detail)
        assert detail["code"] == "daily_limit_exceeded"
        assert detail["limit"] == 25
        assert detail["used"] == 30
        assert detail["remaining"] == 0
