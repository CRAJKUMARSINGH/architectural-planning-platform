"""Database-backed authorization for project-scoped API dependencies.

Token claims identify the subject and requested organization, but never grant
access by themselves.  The active database membership is the authority for
both role and account status, preserving the organization boundary described
in ADR-003.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api import auth
from services.api.auth import AuthUser, CurrentUser
from services.api.db.session import get_session
from services.api.models.orm import Membership, User


def require_membership_role(minimum_role: str) -> Any:
    """Build a dependency that checks active membership and effective role."""

    def _check(
        user: AuthUser,
        session: Session = Depends(get_session),
    ) -> CurrentUser:
        # Local development intentionally uses the seeded dev identity without
        # requiring a database row; staging/production cannot use this branch.
        if auth.AUTH_DISABLED:
            if not user.has_role(minimum_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{minimum_role}' required, you have '{user.role}'",
                )
            return user

        membership = session.execute(
            select(Membership.role, User.disabled_at, User.deleted_at)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.organization_id == user.org_id,
                Membership.user_id == user.user_id,
            )
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active organization membership required",
            )
        member_role, disabled_at, deleted_at = membership
        if disabled_at is not None or deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        # Replace untrusted token role with the role held in the database.
        user.role = member_role
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{minimum_role}' required, you have '{member_role}'",
            )
        return user

    return Depends(_check)


require_project_viewer = require_membership_role("viewer")
require_project_editor = require_membership_role("editor")
require_project_owner = require_membership_role("owner")
