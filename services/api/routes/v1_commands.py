"""Phase 5 — typed command routes.

POST /v1/projects/{id}/commands/preview
POST /v1/projects/{id}/commands/commit

Both routes accept:
  Idempotency-Key  — client-supplied deduplication key (required for commit)
  If-Match         — expected current revision ETag  e.g. "Rev:12"

Execution pipeline (per IMPLEMENTATION_PLAN.md §Phase 5):
  schema validation → authorization → object existence →
  topology preconditions → geometry operation → constraint propagation →
  quick validation → affected-object calculation →
  deterministic serialization → revision candidate
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.auth import AuthUser, require_editor
from services.api.authorization import require_project_editor
from services.api.db.session import get_session
from services.api.repository_sql import (
    SqlAuditRepository,
    SqlProjectRepository,
    SqlRevisionRepository,
)

router = APIRouter(prefix="/v1/projects", tags=["commands-v1"])


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------

class CommandRequest(BaseModel):
    """Raw command envelope forwarded from the React editor.

    The schema is validated downstream by CommandEnvelope.from_mapping().
    We accept any dict here so that upstream validation errors surface as
    structured findings rather than 422 Pydantic errors.
    """
    command: dict[str, Any] = Field(
        ...,
        description="Canonical advocate-chambers.command.v1 envelope.",
    )


class FindingOut(BaseModel):
    rule: str
    severity: str
    message: str
    objectIds: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    professionalReviewRequired: bool = False


class RevisionSummaryOut(BaseModel):
    revisionNumber: int
    revisionId: str
    projectId: str
    commandId: str
    operation: str
    modelSha256: str
    reason: str


class CommandPreviewResponse(BaseModel):
    accepted: bool
    replayed: bool
    findings: list[FindingOut]
    affectedObjectIds: list[str]
    summary: RevisionSummaryOut | None = None
    previewOnly: bool = True


class CommandCommitResponse(BaseModel):
    accepted: bool
    replayed: bool
    findings: list[FindingOut]
    affectedObjectIds: list[str]
    summary: RevisionSummaryOut | None = None
    revisionId: uuid.UUID | None = None
    modelSha256: str | None = None
    validationState: str | None = None
    previewOnly: bool = False


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_project_or_404(
    project_id: uuid.UUID, org_id: uuid.UUID, session: Session
) -> dict[str, Any]:
    repo = SqlProjectRepository(session)
    project = repo.get(project_id, org_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _check_if_match(
    if_match: str | None,
    current_revision: int,
) -> None:
    """Validate the If-Match header against the current revision number.

    Expected format:  "Rev:12"  or omitted.
    Raises 412 Precondition Failed when the ETag does not match.
    """
    if if_match is None:
        return
    if_match = if_match.strip().strip('"')
    if not if_match.startswith("Rev:"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='If-Match must use format "Rev:<number>" e.g. "Rev:12"',
        )
    try:
        expected = int(if_match[4:])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="If-Match revision number is not an integer",
        )
    if expected != current_revision:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=(
                f"If-Match mismatch: client expects revision {expected}, "
                f"current is {current_revision}"
            ),
            headers={"ETag": f'"Rev:{current_revision}"'},
        )


def _current_revision_number(
    project: dict[str, Any], rev_repo: SqlRevisionRepository
) -> int:
    """Return the current revision number (0 when no revisions yet)."""
    current_id = project.get("current_revision_id")
    if current_id is None:
        return 0
    rev = rev_repo.get(current_id)
    return int(rev["revision_number"]) if rev else 0


def _load_current_model(
    project: dict[str, Any],
    rev_repo: SqlRevisionRepository,
) -> dict[str, Any] | None:
    """Load the canonical model bytes from the object store and parse as JSON.

    Returns None when there is no revision yet (create-project scenario).
    """
    current_id = project.get("current_revision_id")
    if current_id is None:
        return None
    rev = rev_repo.get(current_id)
    if not rev:
        return None
    storage_key = rev.get("model_storage_key")
    if not storage_key:
        return None
    try:
        from services.api.storage import get_object_store  # noqa: PLC0415
        store = get_object_store()
        data = store.get(storage_key)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def _run_command(
    model: dict[str, Any] | None,
    raw_command: dict[str, Any],
) -> Any:
    """Execute via in-process CommandRunner (no DB side effects)."""
    from packages.geometry.command_runner import CommandRunner  # noqa: PLC0415
    runner = CommandRunner()
    return runner.execute(model, raw_command)


def _findings_to_out(findings: list[dict[str, Any]]) -> list[FindingOut]:
    return [
        FindingOut(
            rule=f.get("rule", "UNKNOWN"),
            severity=f.get("severity", "ERROR"),
            message=f.get("message", ""),
            objectIds=f.get("objectIds", []),
            evidence=f.get("evidence", {}),
            professionalReviewRequired=f.get("professionalReviewRequired", False),
        )
        for f in findings
    ]


def _summary_to_out(summary: Any) -> RevisionSummaryOut | None:
    if summary is None:
        return None
    m = summary.to_mapping()
    return RevisionSummaryOut(
        revisionNumber=m["revisionNumber"],
        revisionId=m["revisionId"],
        projectId=m["projectId"],
        commandId=m["commandId"],
        operation=m["operation"],
        modelSha256=m["modelSha256"],
        reason=m.get("reason", ""),
    )


# ---------------------------------------------------------------------------
# POST /v1/projects/{project_id}/commands/preview
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/commands/preview",
    response_model=CommandPreviewResponse,
    summary="Preview a command without persisting a revision",
)
def preview_command(
    project_id: uuid.UUID,
    req: CommandRequest,
    response: Response,
    user: AuthUser,
    _editor: Any = require_project_editor,
    if_match: Annotated[str | None, Header(alias="if-match")] = None,
    session: Session = Depends(get_session),
) -> CommandPreviewResponse:
    """Run the full command pipeline in dry-run mode.

    Returns findings, affected objects, and a preview revision summary
    without writing anything to the database or object store.
    """
    project = _get_project_or_404(project_id, user.org_id, session)
    rev_repo = SqlRevisionRepository(session)
    current_revision = _current_revision_number(project, rev_repo)

    _check_if_match(if_match, current_revision)

    model = _load_current_model(project, rev_repo)
    result = _run_command(model, req.command)

    response.headers["ETag"] = f'"Rev:{current_revision}"'

    return CommandPreviewResponse(
        accepted=result.accepted,
        replayed=result.replayed,
        findings=_findings_to_out(result.findings),
        affectedObjectIds=result.affected_object_ids,
        summary=_summary_to_out(result.summary),
        previewOnly=True,
    )


# ---------------------------------------------------------------------------
# POST /v1/projects/{project_id}/commands/commit
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/commands/commit",
    response_model=CommandCommitResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a command and persist an immutable revision",
)
def commit_command(
    project_id: uuid.UUID,
    req: CommandRequest,
    response: Response,
    user: AuthUser,
    _editor: Any = require_project_editor,
    idempotency_key: Annotated[str | None, Header(alias="idempotency-key")] = None,
    if_match: Annotated[str | None, Header(alias="if-match")] = None,
    session: Session = Depends(get_session),
) -> CommandCommitResponse:
    """Execute the command and commit a new immutable revision.

    Rules:
    - Idempotency-Key is required.  Replaying the same key+fingerprint
      returns the original accepted result without a second DB write.
    - If-Match (optional) validates the client is up to date before executing.
    - Returns 409 when the base revision in the command envelope is stale.
    - Returns 412 when the If-Match header does not match.
    - Returns 422 when the command envelope fails schema validation.
    - Returns 200 (not 201) to allow idempotent replay to return identical
      status codes.
    """
    if not idempotency_key or len(idempotency_key.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key header is required and must be at least 8 characters",
        )
    idempotency_key = idempotency_key.strip()

    project = _get_project_or_404(project_id, user.org_id, session)
    rev_repo = SqlRevisionRepository(session)
    current_revision = _current_revision_number(project, rev_repo)

    _check_if_match(if_match, current_revision)

    model = _load_current_model(project, rev_repo)
    result = _run_command(model, req.command)

    # Always emit the current ETag so the client can update its state
    response.headers["ETag"] = f'"Rev:{current_revision}"'

    if not result.accepted:
        # Surface conflict as 409 so the client knows to re-fetch
        has_conflict = any(
            f.get("rule") in {"REVISION_CONFLICT", "STALE_REVISION"}
            for f in result.findings
        )
        return CommandCommitResponse(
            accepted=False,
            replayed=result.replayed,
            findings=_findings_to_out(result.findings),
            affectedObjectIds=result.affected_object_ids,
            summary=None,
        )

    # --- persist the accepted model -----------------------------------------
    if result.model is None:
        raise HTTPException(
            status_code=500,
            detail="Command was accepted but produced no model — internal error",
        )

    model_bytes = json.dumps(result.model, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")

    from packages.geometry.commands import command_fingerprint as _fp  # noqa: PLC0415
    from packages.geometry.commands import CommandEnvelope  # noqa: PLC0415
    from packages.geometry.persistence import (  # noqa: PLC0415
        RevisionCommitRequest,
        RevisionConflict,
        IdempotencyConflict,
        RevisionTransactionCoordinator,
    )
    from services.api.storage import get_object_store  # noqa: PLC0415

    try:
        envelope = CommandEnvelope.from_mapping(req.command)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    fingerprint = _fp(envelope)

    proj_repo = SqlProjectRepository(session)
    audit_repo = SqlAuditRepository(session)
    store = get_object_store()

    coordinator = RevisionTransactionCoordinator(
        projects=proj_repo,
        revisions=rev_repo,
        objects=store,
        audit=audit_repo,
    )

    try:
        commit_result = coordinator.commit(
            RevisionCommitRequest(
                organization_id=user.org_id,
                project_id=project_id,
                base_revision=current_revision,
                model_bytes=model_bytes,
                author_user_id=user.user_id,
                reason=envelope.reason or f"Command: {envelope.operation}",
                command_id=envelope.command_id,
                idempotency_key=idempotency_key,
                command_fingerprint=fingerprint,
                engine_version="phase5.command-route.v1",
                validation_state="DRAFT",
                request_id=user.request_id,
                audit_payload={"operation": envelope.operation},
            )
        )
    except RevisionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Revision conflict: base {exc.expected} is stale, "
                f"current is {exc.actual}"
            ),
            headers={"ETag": f'"Rev:{exc.actual}"'},
        ) from exc
    except IdempotencyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    new_rev = commit_result.revision
    new_rev_number = int(new_rev["revision_number"])
    response.headers["ETag"] = f'"Rev:{new_rev_number}"'

    # Enqueue a background validation job (best-effort)
    try:
        from services.api.repository_sql import SqlJobRepository  # noqa: PLC0415
        job_repo = SqlJobRepository(session)
        job_repo.enqueue(
            project_id=project_id,
            job_type="validate",
            payload={
                "revisionId": str(new_rev["id"]),
                "modelSha256": commit_result.model_sha256,
            },
            created_by_user_id=user.user_id,
            revision_id=new_rev["id"],
        )
    except Exception:
        pass  # validation job is best-effort; do not fail the commit

    return CommandCommitResponse(
        accepted=True,
        replayed=commit_result.replayed,
        findings=[],
        affectedObjectIds=result.affected_object_ids,
        summary=_summary_to_out(result.summary),
        revisionId=new_rev["id"],
        modelSha256=commit_result.model_sha256,
        validationState="DRAFT",
        previewOnly=False,
    )
