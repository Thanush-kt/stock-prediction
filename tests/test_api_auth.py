"""Tests for Clerk JWT authentication dependency and protected endpoints."""
from __future__ import annotations

import datetime as dt
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from packages.shared import config
from packages.shared.models import Position, Ticker
from services.api.deps import ClerkUser, get_current_user, get_session
from services.api.main import app


# Generate deterministic RSA key pairs for testing
_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
TEST_PRIVATE_PEM = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

TEST_PUBLIC_PEM = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")

# A secondary key pair to simulate invalid signatures
_untrusted_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
UNTRUSTED_PRIVATE_PEM = _untrusted_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

TEST_ISSUER = "https://clerk.test.example.com"
TEST_AUDIENCE = "stock-prediction-api"


def make_jwt(
    sub: str | None = "user_test_123",
    sid: str | None = "sess_test_abc",
    iss: str | None = TEST_ISSUER,
    aud: str | None = TEST_AUDIENCE,
    exp_delta: int = 3600,
    private_pem: str = TEST_PRIVATE_PEM,
) -> str:
    """Generate a test JWT with configurable claims and signing key."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "iat": now,
        "nbf": now - 10,
        "exp": now + exp_delta,
    }
    if sub is not None:
        payload["sub"] = sub
    if sid is not None:
        payload["sid"] = sid
    if iss is not None:
        payload["iss"] = iss
    if aud is not None:
        payload["aud"] = aud

    return jwt.encode(payload, private_pem, algorithm="RS256")


@pytest.fixture(name="auth_client")
def fixture_auth_client(session, monkeypatch):
    """TestClient configured with SQLite session and test Clerk PEM settings."""
    app.dependency_overrides[get_session] = lambda: session

    # Configure Settings to use our test PEM key, issuer, and audience
    test_settings = config.Settings(
        database_url="sqlite+pysqlite:///:memory:",
        clerk_pem_public_key=TEST_PUBLIC_PEM,
        clerk_issuer=TEST_ISSUER,
        clerk_audience=TEST_AUDIENCE,
    )
    monkeypatch.setattr(config, "_settings", test_settings)

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_healthz_is_public(auth_client):
    """GET /healthz remains public without credentials."""
    resp = auth_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    ["/positions", "/signals", "/orders", "/equity", "/predictions", "/stocks", "/predictions/latest"],
)
def test_missing_token_returns_401(auth_client, path):
    """Protected endpoints reject requests missing the Authorization header."""
    resp = auth_client.get(path)
    assert resp.status_code == 401
    assert "Missing authorization header" in resp.json()["detail"]
    assert "WWW-Authenticate" in resp.headers


@pytest.mark.parametrize(
    "auth_header, expected_detail",
    [
        ("Token xyz", "Invalid authorization header; expected Bearer token"),
        ("Basic dXNlcjpwYXNz", "Invalid authorization header; expected Bearer token"),
        ("Bearer ", "Invalid authorization header; expected Bearer token"),
        ("Bearer   ", "Invalid authorization header; expected Bearer token"),
    ],
)
def test_malformed_auth_header_returns_401(auth_client, auth_header, expected_detail):
    """Non-Bearer or empty bearer tokens return HTTP 401."""
    resp = auth_client.get("/positions", headers={"Authorization": auth_header})
    assert resp.status_code == 401
    assert expected_detail in resp.json()["detail"]
    assert "WWW-Authenticate" in resp.headers


def test_invalid_signature_returns_401(auth_client):
    """Token signed by an untrusted key is rejected with HTTP 401."""
    token = make_jwt(private_pem=UNTRUSTED_PRIVATE_PEM)
    resp = auth_client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Invalid authentication token" in resp.json()["detail"]


def test_expired_token_returns_401(auth_client):
    """Token with expired timestamp returns HTTP 401."""
    token = make_jwt(exp_delta=-3600)
    resp = auth_client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["detail"]


def test_invalid_issuer_returns_401(auth_client):
    """Token with unmatching issuer returns HTTP 401."""
    token = make_jwt(iss="https://untrusted-issuer.example.com")
    resp = auth_client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Invalid token issuer" in resp.json()["detail"]


def test_invalid_audience_returns_401(auth_client):
    """Token with unmatching audience returns HTTP 401."""
    token = make_jwt(aud="wrong-audience")
    resp = auth_client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Invalid token audience" in resp.json()["detail"]


def test_missing_subject_claim_returns_401(auth_client):
    """Token without sub claim returns HTTP 401."""
    token = make_jwt(sub=None)
    resp = auth_client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Token missing subject claim" in resp.json()["detail"]


@pytest.mark.parametrize(
    "path",
    ["/positions", "/signals", "/orders", "/equity", "/predictions", "/stocks", "/predictions/latest"],
)
def test_valid_token_accesses_protected_endpoints(auth_client, path):
    """Valid signed token successfully authenticates and accesses all protected endpoints."""
    token = make_jwt(sub="user_valid_456")
    resp = auth_client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_misconfigured_server_returns_500(session, monkeypatch):
    """When server has neither PEM key nor JWKS configured, fail securely with 500."""
    app.dependency_overrides[get_session] = lambda: session
    unconfigured_settings = config.Settings(
        database_url="sqlite+pysqlite:///:memory:",
        clerk_pem_public_key="",
        clerk_jwks_url="",
        clerk_publishable_key="",
    )
    monkeypatch.setattr(config, "_settings", unconfigured_settings)

    token = make_jwt()
    client = TestClient(app)
    resp = client.get("/positions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 500
    assert "Authentication configuration missing on server" in resp.json()["detail"]
    app.dependency_overrides.clear()


def test_dependency_override_works_in_tests(session):
    """Verify that test suites can override get_current_user with ClerkUser."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: ClerkUser(user_id="mocked_user")

    client = TestClient(app)
    # No auth header needed when dependency is explicitly overridden in tests
    resp = client.get("/positions")
    assert resp.status_code == 200
    app.dependency_overrides.clear()
