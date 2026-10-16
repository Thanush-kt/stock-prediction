"""FastAPI dependencies — DB session and Clerk authentication."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from packages.shared.config import get_settings
from packages.shared.db import get_sessionmaker
from packages.shared.logging import get_logger

log = get_logger(__name__)

security_bearer = HTTPBearer(auto_error=False)

_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def reset_jwks_cache_for_tests() -> None:
    """Clear cached PyJWKClient instances (used in tests)."""
    global _jwks_clients  # pylint: disable=global-statement
    _jwks_clients = {}


def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    """Return or initialize a cached PyJWKClient instance for the given JWKS URL."""
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_clients[jwks_url]


@dataclass
class ClerkUser:
    """Authenticated Clerk user information extracted from verified JWT."""
    user_id: str
    session_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


def get_session() -> Iterator[Session]:
    """Open a DB session for the request and close it afterwards.

    Tests override this dependency to use the in-memory SQLite fixture.
    """
    sm = get_sessionmaker()
    session = sm()
    try:
        yield session
    finally:
        session.close()


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> ClerkUser:
    """Validate Clerk session Bearer token from the Authorization header.

    Rejects missing, expired, malformed, or incorrectly signed tokens with HTTP 401.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not creds or not creds.credentials:
        # Header present but not valid Bearer format
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header; expected Bearer token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    token = creds.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    pem_key = settings.clerk_pem_public_key.strip()
    jwks_url = settings.resolved_clerk_jwks_url.strip()

    if not pem_key and not jwks_url:
        log.error("Clerk auth misconfigured: neither CLERK_PEM_PUBLIC_KEY nor JWKS URL resolved")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication configuration missing on server",
        )

    # Determine signing key
    signing_key: Any
    if pem_key:
        signing_key = pem_key
    else:
        try:
            jwks_client = _get_jwks_client(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token).key
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log.warning("Could not retrieve signing key from JWKS: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signing key",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            ) from exc

    # Validate claims
    expected_iss = settings.resolved_clerk_issuer.strip()
    expected_aud = settings.clerk_audience.strip()

    decode_options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_nbf": True,
        "verify_iat": True,
        "verify_aud": bool(expected_aud),
        "verify_iss": bool(expected_iss),
    }

    decode_kwargs: dict[str, Any] = {
        "algorithms": ["RS256", "ES256", "RS384", "RS512"],
        "options": decode_options,
    }
    if expected_aud:
        decode_kwargs["audience"] = expected_aud
    if expected_iss:
        decode_kwargs["issuer"] = expected_iss

    try:
        payload = jwt.decode(token, signing_key, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token has expired"'
            },
        ) from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid token issuer"'
            },
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid token audience"'
            },
        ) from exc
    except jwt.PyJWTError as exc:
        log.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    return ClerkUser(
        user_id=str(user_id),
        session_id=payload.get("sid"),
        claims=payload,
    )

