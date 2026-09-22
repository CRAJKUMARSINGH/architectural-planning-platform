"""Authentication primitives — Phase 4 / E03 Auth & Tenancy.

Production tokens are validated against an OIDC issuer and rotating JWKS keys.
The shared-secret path remains available for local/test deployments, but a
default development secret is never accepted in staging or production.
Organization membership and the effective role are checked by
``services.api.authorization`` before project-scoped routes execute.

Roles: owner | editor | viewer | reviewer
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AUTH_DISABLED: bool = os.environ.get("AUTH_DISABLED", "false").lower() == "true"
ENVIRONMENT: str = os.environ.get("ENV", "development").lower()
JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
OIDC_ISSUER: str = os.environ.get("OIDC_ISSUER", "").rstrip("/")
OIDC_AUDIENCE: str = os.environ.get("OIDC_AUDIENCE", "")
OIDC_JWKS_URL: str = os.environ.get(
    "OIDC_JWKS_URL",
    f"{OIDC_ISSUER}/.well-known/jwks.json" if OIDC_ISSUER else "",
)
CLOCK_SKEW_SECONDS: int = int(os.environ.get("AUTH_CLOCK_SKEW_SECONDS", "60"))
DEFAULT_DEV_SECRET = "dev-secret-change-in-production"

# Dev seeded user / org (only used when AUTH_DISABLED=true)
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEV_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Role hierarchy — an owner has all editor+viewer rights, etc.
ROLE_WEIGHT: dict[str, int] = {
    "viewer": 1,
    "reviewer": 2,
    "editor": 3,
    "owner": 4,
}
VALID_ROLES = frozenset(ROLE_WEIGHT)


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID
    role: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    external_auth_id: str | None = None

    def has_role(self, minimum: str) -> bool:
        return ROLE_WEIGHT.get(self.role, 0) >= ROLE_WEIGHT.get(minimum, 99)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def auth_configuration_errors() -> list[str]:
    """Return deployment configuration violations without exposing secrets."""
    errors: list[str] = []
    if ENVIRONMENT in {"staging", "production", "prod"} and AUTH_DISABLED:
        errors.append("AUTH_DISABLED must be false in staging and production")
    if (
        ENVIRONMENT in {"staging", "production", "prod"}
        and not OIDC_ISSUER
        and (not JWT_SECRET or JWT_SECRET == DEFAULT_DEV_SECRET)
    ):
        errors.append("OIDC_ISSUER or a non-development JWT_SECRET is required")
    if OIDC_ISSUER and not OIDC_AUDIENCE:
        errors.append("OIDC_AUDIENCE is required when OIDC_ISSUER is configured")
    if OIDC_ISSUER and not OIDC_JWKS_URL:
        errors.append("OIDC_JWKS_URL is required when OIDC_ISSUER is configured")
    if CLOCK_SKEW_SECONDS < 0 or CLOCK_SKEW_SECONDS > 300:
        errors.append("AUTH_CLOCK_SKEW_SECONDS must be between 0 and 300")
    return errors


def assert_auth_configuration() -> None:
    """Fail closed when deployment authentication settings are unsafe."""
    errors = auth_configuration_errors()
    if errors:
        raise RuntimeError("Invalid authentication configuration: " + "; ".join(errors))


def _decode_jwt(token: str) -> dict:
    """Decode and verify a local or OIDC JWT with expiry and issuer checks."""
    try:
        import jwt  # type: ignore[import]
        if OIDC_ISSUER:
            if not OIDC_AUDIENCE:
                raise ValueError("OIDC_AUDIENCE is not configured")
            if not OIDC_JWKS_URL:
                raise ValueError("OIDC_JWKS_URL is not configured")
            signing_key = jwt.PyJWKClient(OIDC_JWKS_URL).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                audience=OIDC_AUDIENCE,
                issuer=OIDC_ISSUER,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "sub"]},
            )
        if not JWT_SECRET:
            raise ValueError("JWT_SECRET is not configured")
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["exp", "sub"]},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Extract and validate the current user from the Authorization header.

    If AUTH_DISABLED=true (local dev only), returns the seeded dev user.
    NEVER enable AUTH_DISABLED in staging or production (see ADR-003).
    """
    request_id = x_request_id or str(uuid.uuid4())

    if AUTH_DISABLED:
        return CurrentUser(
            user_id=DEV_USER_ID,
            email="dev@local.example",
            org_id=DEV_ORG_ID,
            role="owner",
            request_id=request_id,
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_jwt(token)

    try:
        role = payload.get("role", "viewer")
        if role not in VALID_ROLES:
            raise ValueError(f"unsupported role: {role!r}")
        if payload.get("disabled") is True or payload.get("is_active") is False:
            raise PermissionError("user account is disabled")
        return CurrentUser(
            user_id=uuid.UUID(payload["sub"]),
            email=payload.get("email", ""),
            org_id=uuid.UUID(payload["org_id"]),
            role=role,
            request_id=request_id,
            external_auth_id=str(payload["sub"]),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token payload invalid: {exc}",
        ) from exc


# Typed aliases for FastAPI injection
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(minimum_role: str):
    """Return a FastAPI dependency that enforces a minimum role."""
    def _check(user: AuthUser) -> CurrentUser:
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{minimum_role}' required, you have '{user.role}'",
            )
        return user
    return Depends(_check)


# Convenience role deps
require_viewer = require_role("viewer")
require_editor = require_role("editor")
require_owner = require_role("owner")
