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


# ---------------------------------------------------------------------------
# Phase 5 vertical slice — canonical analysis endpoint (ticket #9 + #12)
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    """Versioned canonical analysis — drives the Viewport2D component."""
    reportVersion: str = ""
    status: str = "unavailable"
    spaces: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)
    openings: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    findingCounts: dict[str, int] = Field(default_factory=dict)
    # Optional enriched fields — present when the geometry engine is available
    week5: dict[str, Any] | None = None
    week6: dict[str, Any] | None = None
    connectors: list[dict[str, Any]] | None = None
    program: dict[str, Any] | None = None
    orientation: dict[str, Any] | None = None
    adjacencies: list[dict[str, Any]] | None = None
    week7: dict[str, Any] | None = None
    week8: dict[str, Any] | None = None
    rulePack: dict[str, Any] | None = None
    drawingQuality: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


@router.get("/{project_id}/analysis", response_model=AnalysisResponse)
def get_project_analysis(
    project_id: uuid.UUID,
    level: str | None = None,
    user: AuthUser = None,  # type: ignore[assignment]
    _: Any = require_project_viewer,
    session: Session = Depends(get_session),
) -> AnalysisResponse:
    """Return the canonical geometry analysis for a project level.

    This is the versioned, auth-protected replacement for the legacy /analysis
    endpoint.  The React Viewport2D component calls this route.

    When the geometry engine is available the response includes the full
    Week 3–8 enrichment graph.  When the engine is unavailable the endpoint
    returns an unavailable sentinel so the UI can render a graceful fallback
    instead of surfacing a 503.
    """
    # --- org access guard ------------------------------------------------
    proj_repo = SqlProjectRepository(session)
    proj = proj_repo.get(project_id, user.org_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # --- geometry engine ------------------------------------------------
    # The actual analysis is produced by the week34/56/78 enrichment pipeline
    # living in scripts/.  We delegate to the legacy /analysis logic rather
    # than duplicate it, keeping a single source of truth.
    import sys  # noqa: PLC0415
    from pathlib import Path as _Path  # noqa: PLC0415

    _root = _Path(__file__).resolve().parents[3]
    _ba = _root / "bar-association-hall"
    for _p in (str(_root / "scripts"), str(_ba)):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    try:
        from drawing_model import load_model  # type: ignore[import]  # noqa: PLC0415
        from week34 import enrichment_report  # type: ignore[import]  # noqa: PLC0415
        from week56 import enrichment_report as week56_report  # type: ignore[import]  # noqa: PLC0415
        from week78 import enrichment_report as week78_report  # type: ignore[import]  # noqa: PLC0415
        from week2 import load_canonical_model  # type: ignore[import]  # noqa: PLC0415
    except ImportError:
        # Geometry engine not available — return a well-structured unavailable
        # sentinel rather than a 503 so the viewport degrades gracefully.
        return AnalysisResponse(
            status="engine-unavailable",
            graph={"nodes": [], "edges": [], "routes": []},
        )

    try:
        site, plans = load_model()
        report = enrichment_report(site, plans)
        canonical = load_canonical_model()
        coordination = week56_report(canonical)
        enriched = week78_report(canonical)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}") from exc

    # --- filter by level -----------------------------------------------
    selected_level = level if level in {"GF", "FF"} else None

    spaces = [
        {
            "id": space.get("id"),
            "levelId": space.get("level"),
            "name": space.get("name"),
            "rect": space.get("rect"),
            "roomUse": space.get("roomUse"),
        }
        for space in plans.get("spaces", [])
        if selected_level is None or space.get("level") == selected_level
    ]

    graph = report["week3"]["graph"]
    graph["nodes"] = [
        node for node in graph["nodes"]
        if selected_level is None
        or node.get("levelId") == selected_level
        or node.get("kind") == "exterior-zone"
    ]
    node_ids = {node["id"] for node in graph["nodes"]}
    graph["edges"] = [
        edge for edge in graph["edges"]
        if edge.get("from") in node_ids and edge.get("to") in node_ids
    ]
    graph["routes"] = [
        route for route in graph["routes"]
        if selected_level is None or route.get("levelId") == selected_level
    ]

    schedule = [
        item for item in report["week4"]["schedule"]
        if selected_level is None or item.get("levelId") == selected_level
    ]
    findings: list[dict[str, Any]] = [
        f for f in report["findings"]
        if selected_level is None or f.get("levelId") == selected_level
    ]
    findings.extend(
        f for f in (
            coordination["week5"]["findings"] + coordination["week6"]["findings"]
        )
        if selected_level is None or f.get("levelId") in {None, selected_level}
    )
    findings.extend(
        f for f in (
            enriched["week7"]["findings"] + enriched["week8"]["findings"]
        )
        if selected_level is None or f.get("levelId") in {None, selected_level}
    )

    return AnalysisResponse(
        reportVersion=enriched.get("reportVersion", ""),
        status=enriched.get("status", "REVIEW_REQUIRED"),
        findingCounts={
            sev: sum(1 for f in findings if f["severity"] == sev)
            for sev in ("BLOCKER", "ERROR", "WARNING")
            if any(f["severity"] == sev for f in findings)
        },
        spaces=spaces,
        graph=graph,
        openings=schedule,
        findings=findings,
        week5=coordination.get("week5"),
        week6=coordination.get("week6"),
        connectors=coordination.get("week5", {}).get("connectors"),
        program=coordination.get("week6", {}).get("program"),
        orientation=coordination.get("week6", {}).get("program", {}).get("orientation"),
        adjacencies=coordination.get("week6", {}).get("program", {}).get("adjacencyEvaluations"),
        week7=enriched.get("week7"),
        week8=enriched.get("week8"),
        rulePack=enriched.get("week7", {}).get("selectedRulePack"),
        drawingQuality=enriched.get("week8"),
    )
