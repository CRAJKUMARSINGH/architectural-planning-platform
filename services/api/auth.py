"""Authentication & authorization — E03 Auth & Tenancy.

Strategy:
  - JWT (HS256 or RS256) validated by FastAPI dependency.
  - AUTH_DISABLED=true allows local single-developer mode (never in staging/prod).
  - Organization isolation enforced by requiring org membership in every
    project-scoped operation (ADR-003).

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
JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM: str = "HS256"

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


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID
    role: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def has_role(self, minimum: str) -> bool:
        return ROLE_WEIGHT.get(self.role, 0) >= ROLE_WEIGHT.get(minimum, 99)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def _decode_jwt(token: str) -> dict:
    """Decode and verify a JWT. Falls back to no-op in AUTH_DISABLED mode."""
    try:
        import jwt  # type: ignore[import]
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
        return CurrentUser(
            user_id=uuid.UUID(payload["sub"]),
            email=payload.get("email", ""),
            org_id=uuid.UUID(payload["org_id"]),
            role=payload.get("role", "viewer"),
            request_id=request_id,
        )
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
