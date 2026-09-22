"""Authenticated collaboration and public immutable review-link routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from services.api.auth import AuthUser
from services.api.authorization import (
    require_project_editor,
    require_project_reviewer,
    require_project_viewer,
)
from services.api.collaboration import (
    create_review_token,
    hash_review_token,
    sanitize_viewpoint,
    validate_anchor,
    validate_approval_transition,
    validate_review_view,
)
from services.api.db.session import get_session
from services.api.repository_sql import (
    SqlAuditRepository,
    SqlCollaborationRepository,
    SqlProjectRepository,
    SqlRevisionRepository,
)

router = APIRouter(prefix="/v1/projects", tags=["collaboration-v1"])
public_router = APIRouter(prefix="/v1/review-links", tags=["review-links"])


class ReviewLinkCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    revision_id: uuid.UUID = Field(alias="revisionId")
    view: str = Field(default="technical", min_length=1, max_length=20)
    expires_at: datetime | None = Field(default=None, alias="expiresAt")


class ReviewLinkResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    revision_id: uuid.UUID
    view: str
    created_by_user_id: uuid.UUID | None
    expires_at: datetime | None
    created_at: datetime
    token: str | None = None
    url: str | None = None


class ReviewCommentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    revision_id: uuid.UUID = Field(alias="revisionId")
    anchor_type: str = Field(alias="anchorType", min_length=1, max_length=30)
    anchor_id: str = Field(alias="anchorId", min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    viewpoint: dict[str, Any] | None = None


class ApprovalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    revision_id: uuid.UUID = Field(alias="revisionId")
    state: str = Field(..., min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=5000)


def _project_revision(
    project_id: uuid.UUID,
    revision_id: uuid.UUID,
    user: AuthUser,
    session: Session,
) -> dict[str, Any]:
    project = SqlProjectRepository(session).get(project_id, user.org_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    revision = SqlRevisionRepository(session).get_for_project(project_id, revision_id)
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    return revision


def _without_secret(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result.pop("token_hash", None)
    return result


@router.post(
    "/{project_id}/review-links",
    response_model=ReviewLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review_link(
    project_id: uuid.UUID,
    req: ReviewLinkCreateRequest,
    user: AuthUser,
    _: Any = require_project_editor,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _project_revision(project_id, req.revision_id, user, session)
    try:
        view = validate_review_view(req.view)
        token, token_hash = create_review_token()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = SqlCollaborationRepository(session).create_review_link(
        project_id,
        req.revision_id,
        token_hash,
        view,
        user.user_id,
        req.expires_at,
    )
    SqlAuditRepository(session).record(
        action="review_link.create",
        resource_type="review_link",
        resource_id=str(row["id"]),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        payload={"project_id": str(project_id), "revision_id": str(req.revision_id), "view": view},
        request_id=user.request_id,
    )
    result = _without_secret(row)
    result["token"] = token
    result["url"] = f"/api/v1/review-links/{token}"
    return result


@router.get("/{project_id}/review-links", response_model=list[ReviewLinkResponse])
def list_review_links(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if not SqlProjectRepository(session).get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return [_without_secret(row) for row in SqlCollaborationRepository(session).list_review_links(project_id)]


@router.post("/{project_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    project_id: uuid.UUID,
    req: ReviewCommentCreateRequest,
    user: AuthUser,
    _: Any = require_project_reviewer,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _project_revision(project_id, req.revision_id, user, session)
    try:
        anchor_type, anchor_id = validate_anchor(req.anchor_type, req.anchor_id)
        viewpoint = sanitize_viewpoint(req.viewpoint)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = SqlCollaborationRepository(session).create_comment(
        project_id,
        req.revision_id,
        user.user_id,
        anchor_type,
        anchor_id,
        req.body.strip(),
        viewpoint,
    )
    SqlAuditRepository(session).record(
        action="review_comment.create",
        resource_type="review_comment",
        resource_id=str(row["id"]),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        payload={"project_id": str(project_id), "revision_id": str(req.revision_id), "anchor_type": anchor_type},
        request_id=user.request_id,
    )
    return row


@router.get("/{project_id}/comments")
def list_comments(
    project_id: uuid.UUID,
    user: AuthUser,
    revision_id: uuid.UUID | None = None,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if not SqlProjectRepository(session).get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return SqlCollaborationRepository(session).list_comments(project_id, revision_id)


@router.post("/{project_id}/approvals", status_code=status.HTTP_201_CREATED)
def create_approval(
    project_id: uuid.UUID,
    req: ApprovalCreateRequest,
    user: AuthUser,
    _: Any = require_project_reviewer,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _project_revision(project_id, req.revision_id, user, session)
    repo = SqlCollaborationRepository(session)
    current = repo.latest_approval(project_id)
    previous_state = current["state"] if current else "Draft"
    try:
        state = validate_approval_transition(previous_state, req.state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = repo.create_approval(project_id, req.revision_id, user.user_id, state, req.note)
    SqlAuditRepository(session).record(
        action="review_approval.create",
        resource_type="review_approval",
        resource_id=str(row["id"]),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        payload={"project_id": str(project_id), "revision_id": str(req.revision_id), "state": state},
        request_id=user.request_id,
    )
    return row


@router.get("/{project_id}/approvals")
def list_approvals(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if not SqlProjectRepository(session).get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return SqlCollaborationRepository(session).list_approvals(project_id)


@public_router.get("/{token}")
def resolve_review_link(token: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    try:
        token_hash = hash_review_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Review link not found") from exc
    row = SqlCollaborationRepository(session).get_review_link_by_hash(token_hash)
    now = datetime.now(timezone.utc)
    expires_at = row["expires_at"]
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not row or (expires_at is not None and expires_at <= now):
        raise HTTPException(status_code=404, detail="Review link not found")
    return {
        "id": row["id"],
        "projectId": row["project_id"],
        "revisionId": row["revision_id"],
        "view": row["view"],
        "createdAt": row["created_at"],
        "expiresAt": row["expires_at"],
        "immutable": True,
    }