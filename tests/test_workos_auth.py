import sys
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.requests import Request

from common import global_config
from src.api.auth import workos_auth
from tests.test_template import TestTemplate


def build_request_with_bearer(token: str) -> Request:
    """Create a minimal Starlette request with an Authorization header."""

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "scheme": "http",
        "client": ("testclient", 5000),
    }
    return Request(scope, receive)


class TestWorkOSAuth(TestTemplate):
    """Unit tests for WorkOS JWT authentication."""

    @pytest.fixture()
    def signing_setup(self, monkeypatch):
        """
        Provide an RSA key pair and stub JWKS client so we exercise the
        production verification path (issuer/audience/signature checks).
        """

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        class FakeSigningKey:
            def __init__(self, key):
                self.key = key

        class FakeJWKSClient:
            def get_signing_key_from_jwt(self, token: str):
                return FakeSigningKey(public_key)

        # Mark method as used for static analyzers; the code under test calls it dynamically.
        _ = FakeJWKSClient.get_signing_key_from_jwt

        # Use our fake JWKS client
        monkeypatch.setattr(workos_auth, "get_jwks_client", lambda: FakeJWKSClient())

        # Force non-test mode by removing pytest marker and argv hint
        monkeypatch.delitem(sys.modules, "pytest", raising=False)
        monkeypatch.setattr(sys, "argv", ["main"])

        return private_key

    @pytest.mark.asyncio
    async def test_sys_argv_does_not_enable_test_mode(self, monkeypatch):
        """
        Guardrail: do not disable signature verification based on sys.argv[0].

        Historically, the code treated any argv[0] containing "test" as a signal
        to skip JWT signature verification. That is unsafe because production
        entrypoints can contain "test" in their filename/path.
        """

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        jwks_called = {"value": False}

        class FakeSigningKey:
            def __init__(self, key):
                self.key = key

        class FakeJWKSClient:
            def get_signing_key_from_jwt(self, token: str):
                jwks_called["value"] = True
                return FakeSigningKey(public_key)

        monkeypatch.setattr(workos_auth, "get_jwks_client", lambda: FakeJWKSClient())

        # Simulate a non-pytest runtime with an argv that contains "test".
        monkeypatch.delitem(sys.modules, "pytest", raising=False)
        monkeypatch.setattr(sys, "argv", ["test-server"])
        monkeypatch.delenv("WORKOS_SKIP_JWT_VERIFICATION", raising=False)

        now = int(time.time())
        payload = {
            "sub": "user_id_argv_guardrail",
            "email": "argvguard@example.com",
            "iss": workos_auth.WORKOS_ISSUER,
            "aud": global_config.WORKOS_CLIENT_ID,
            "exp": now + 3600,
            "iat": now,
        }

        token = jwt.encode(payload, private_key, algorithm="RS256")
        request = build_request_with_bearer(token)

        user = await workos_auth.get_current_workos_user(request)
        assert user.id == payload["sub"]
        assert user.email == payload["email"]
        assert jwks_called["value"] is True

    @pytest.mark.asyncio
    async def test_access_token_without_audience_is_accepted(self, signing_setup):
        """Allow access tokens that omit aud but use the access-token issuer."""

        now = int(time.time())
        payload = {
            "sub": "user_access_123",
            "email": "access@example.com",
            "iss": workos_auth.WORKOS_ACCESS_ISSUER,
            "exp": now + 3600,
            "iat": now,
        }

        token = jwt.encode(payload, signing_setup, algorithm="RS256")
        request = build_request_with_bearer(token)

        user = await workos_auth.get_current_workos_user(request)

        assert user.id == payload["sub"]
        assert user.email == payload["email"]

    @pytest.mark.asyncio
    async def test_id_token_with_audience_is_verified(self, signing_setup):
        """Enforce audience when present (ID token path)."""

        now = int(time.time())
        payload = {
            "sub": "user_id_123",
            "email": "idtoken@example.com",
            "iss": workos_auth.WORKOS_ISSUER,
            "aud": global_config.WORKOS_CLIENT_ID,
            "exp": now + 3600,
            "iat": now,
        }

        token = jwt.encode(payload, signing_setup, algorithm="RS256")
        request = build_request_with_bearer(token)

        user = await workos_auth.get_current_workos_user(request)

        assert user.id == payload["sub"]
        assert user.email == payload["email"]

    @pytest.mark.asyncio
    async def test_missing_email_is_fetched_from_workos_api(
        self, signing_setup, monkeypatch
    ):
        """Populate email via WorkOS API when the token omits it."""

        now = int(time.time())
        payload = {
            "sub": "user_access_without_email",
            "iss": workos_auth.WORKOS_ACCESS_ISSUER,
            "exp": now + 3600,
            "iat": now,
        }

        token = jwt.encode(payload, signing_setup, algorithm="RS256")
        request = build_request_with_bearer(token)

        class FakeRemoteUser:
            def __init__(self):
                self.email = "fetched@example.com"
                self.first_name = "Fetched"
                self.last_name = "User"

        class FakeUserManagement:
            def __init__(self):
                self.requested_id = None

            def get_user(self, user_id: str):
                self.requested_id = user_id
                return FakeRemoteUser()

        fake_user_management = FakeUserManagement()
        _ = fake_user_management.get_user(str(payload["sub"]))

        class FakeWorkOSClient:
            def __init__(self):
                self.user_management = fake_user_management

        fake_workos_client = FakeWorkOSClient()
        _ = fake_workos_client.user_management

        monkeypatch.setattr(
            workos_auth, "get_workos_client", lambda: fake_workos_client
        )

        user = await workos_auth.get_current_workos_user(request)

        assert user.id == payload["sub"]
        assert user.email == "fetched@example.com"
        assert user.first_name == "Fetched"
        assert user.last_name == "User"
        assert fake_user_management.requested_id == payload["sub"]

    @pytest.mark.asyncio
    async def test_token_with_untrusted_issuer_is_rejected(self, signing_setup):
        """Reject tokens that are signed but from an issuer outside the allowlist."""

        now = int(time.time())
        payload = {
            "sub": "user_evil_123",
            "email": "evil@example.com",
            "iss": "https://malicious.example.com",
            "aud": global_config.WORKOS_CLIENT_ID,
            "exp": now + 3600,
            "iat": now,
        }

        token = jwt.encode(payload, signing_setup, algorithm="RS256")
        request = build_request_with_bearer(token)

        with pytest.raises(HTTPException) as excinfo:
            await workos_auth.get_current_workos_user(request)

        assert isinstance(excinfo.value, HTTPException)
        assert excinfo.value.status_code == 401
