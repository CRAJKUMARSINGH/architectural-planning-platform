"""E06 versioned /v1/projects routes with auth + org isolation + audit."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.auth import AuthUser, require_editor, require_owner
from services.api.authorization import (
    require_project_editor,
    require_project_owner,
    require_project_viewer,
)
from services.api.db.session import get_session
from services.api.repository_sql import SqlAuditRepository, SqlJobRepository, SqlProjectRepository, SqlRevisionRepository

router = APIRouter(prefix="/v1/projects", tags=["projects-v1"])


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    units: str = Field(default="inch", pattern="^(inch|mm|m|ft)$")


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    units: str


class JobEnqueueRequest(BaseModel):
    job_type: str = Field(..., pattern="^(generate|validate|enrich|quality_gate|export|benchmark)$")
    payload: dict[str, Any] = Field(default_factory=dict)
    revision_id: uuid.UUID | None = None


class JobStatusResponse(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    progress: int
    error: str | None = None


class RevisionResponse(BaseModel):
    """Typed revision summary — returned by GET /v1/projects/{id}/revisions."""
    id: uuid.UUID
    project_id: uuid.UUID
    revision_number: int
    model_sha256: str | None = None
    model_storage_key: str | None = None
    engine_version: str | None = None
    validation_state: str | None = None
    command_id: str | None = None
    idempotency_key: str | None = None
    reason: str | None = None
    author_user_id: uuid.UUID | None = None
    parent_revision_id: uuid.UUID | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[ProjectResponse])
def list_projects(user: AuthUser, session: Session = Depends(get_session)):
    repo = SqlProjectRepository(session)
    return repo.list_for_org(user.org_id)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreateRequest,
    user: AuthUser,
    _: Any = require_project_editor,
    session: Session = Depends(get_session),
):
    repo = SqlProjectRepository(session)
    audit = SqlAuditRepository(session)
    proj = repo.create(user.org_id, req.name, req.units, user.user_id)
    audit.record(
        action="project.create",
        resource_type="project",
        resource_id=str(proj["id"]),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        payload={"name": req.name, "units": req.units},
        request_id=user.request_id,
    )
    return proj


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
):
    repo = SqlProjectRepository(session)
    proj = repo.get(project_id, user.org_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_owner,
    session: Session = Depends(get_session),
):
    repo = SqlProjectRepository(session)
    audit = SqlAuditRepository(session)
    repo.soft_delete(project_id, user.org_id)
    audit.record(
        action="project.delete",
        resource_type="project",
        resource_id=str(project_id),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        request_id=user.request_id,
    )


@router.post("/{project_id}/jobs", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_job(
    project_id: uuid.UUID,
    req: JobEnqueueRequest,
    user: AuthUser,
    _: Any = require_project_editor,
    session: Session = Depends(get_session),
):
    # Verify org access
    proj_repo = SqlProjectRepository(session)
    if not proj_repo.get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")

    job_repo = SqlJobRepository(session)
    audit = SqlAuditRepository(session)
    job = job_repo.enqueue(
        project_id=project_id,
        job_type=req.job_type,
        payload=req.payload,
        created_by_user_id=user.user_id,
        revision_id=req.revision_id,
    )
    audit.record(
        action="job.enqueue",
        resource_type="job",
        resource_id=str(job["id"]),
        organization_id=user.org_id,
        actor_user_id=user.user_id,
        payload={"job_type": req.job_type},
        request_id=user.request_id,
    )

    # Dispatch to RQ worker if available (E04)
    try:
        from services.worker.queue import dispatch_job  # type: ignore[import]
        dispatch_job(str(job["id"]), req.job_type, req.payload)
    except ImportError:
        pass  # Worker queue not yet available in dev-only mode

    return job


@router.get("/{project_id}/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
):
    # Verify org access
    proj_repo = SqlProjectRepository(session)
    if not proj_repo.get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")

    job_repo = SqlJobRepository(session)
    job = job_repo.get(job_id)
    if not job or str(job["project_id"]) != str(project_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{project_id}/revisions", response_model=list[RevisionResponse])
def list_revisions(
    project_id: uuid.UUID,
    user: AuthUser,
    response: Response,
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
):
    proj_repo = SqlProjectRepository(session)
    project = proj_repo.get(project_id, user.org_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    rev_repo = SqlRevisionRepository(session)
    revisions = rev_repo.list_for_project(project_id)
    # Expose current revision number as ETag for If-Match on commands
    current_id = project.get("current_revision_id")
    if current_id:
        current = rev_repo.get(current_id)
        if current:
            response.headers["ETag"] = f'"Rev:{current["revision_number"]}"'
    return [
        RevisionResponse(
            id=r["id"],
            project_id=r["project_id"],
            revision_number=r["revision_number"],
            model_sha256=r.get("model_sha256"),
            model_storage_key=r.get("model_storage_key"),
            engine_version=r.get("engine_version"),
            validation_state=r.get("validation_state"),
            command_id=r.get("command_id"),
            idempotency_key=r.get("idempotency_key"),
            reason=r.get("reason"),
            author_user_id=r.get("author_user_id"),
            parent_revision_id=r.get("parent_revision_id"),
            created_at=str(r["created_at"]) if r.get("created_at") else None,
        )
        for r in revisions
    ]
