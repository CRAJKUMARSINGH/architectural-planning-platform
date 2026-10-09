"""Workflow API routes — Archi Copilot integration.

Implements the full brief → canvas → score → suggest → export workflow
inside the Platform's authenticated API surface.

Endpoint prefix: /api/workflow
Auth:            Platform JWT (same as /api/v1/projects)
Project IDs:     UUID (Platform standard — not Archi Copilot integer IDs)

The AI calls delegate to services/ai/ai_service.py (Gemini).
Canvas blocks are concept-level only — NOT authoritative geometry.
Promote to geometry via POST /api/v1/projects/{id}/jobs with type=generate.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.ai.ai_service import get_ai_service
from services.api.auth import AuthUser, get_current_user
from services.api.authorization import require_project_editor, require_project_viewer
from services.api.db.session import get_session
from services.api.models.workflow_models import (
    BriefAnalysis,
    ConceptVersion,
    CopilotSuggestion,
)
from services.api.repository_sql import SqlProjectRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CanvasBlock(BaseModel):
    id: str
    label: str
    zoneType: str = Field(
        ...,
        pattern="^(living|sleeping|service|circulation|outdoor|work|other)$",
    )
    floor: str
    x: float
    y: float
    width: float
    height: float


class BriefAnalysisOut(BaseModel):
    id: uuid.UUID
    projectId: uuid.UUID
    summary: str
    spaceProgram: list[dict[str, Any]]
    constraints: list[str]
    opportunities: list[str]
    openQuestions: list[str]
    createdAt: str


class VersionInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    floors: list[str] = Field(default_factory=lambda: ["Ground Floor"])
    blocks: list[CanvasBlock]


class VersionOut(BaseModel):
    id: uuid.UUID
    projectId: uuid.UUID
    briefAnalysisId: uuid.UUID | None
    name: str
    floors: list[str]
    blocks: list[dict[str, Any]]
    overallScore: float | None
    programFitScore: float | None
    daylightScore: float | None
    budgetFitScore: float | None
    aiCommentary: str | None
    promotedRevisionId: uuid.UUID | None
    createdAt: str


class SuggestionOut(BaseModel):
    id: uuid.UUID
    projectId: uuid.UUID
    category: str
    text: str
    priority: str
    status: str
    createdAt: str


class SuggestionUpdate(BaseModel):
    status: str = Field(..., pattern="^(new|accepted|dismissed)$")


class ProjectExportOut(BaseModel):
    projectId: uuid.UUID
    briefAnalysis: BriefAnalysisOut | None
    bestVersion: VersionOut | None
    generatedAt: str
    markdown: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _suggestion_hash(category: str, text: str) -> str:
    return hashlib.sha256(f"{category}:{text}".encode()).hexdigest()


def _brief_analysis_to_out(ba: BriefAnalysis) -> BriefAnalysisOut:
    return BriefAnalysisOut(
        id=ba.id,
        projectId=ba.project_id,
        summary=ba.summary,
        spaceProgram=ba.space_program or [],
        constraints=ba.constraints or [],
        opportunities=ba.opportunities or [],
        openQuestions=ba.open_questions or [],
        createdAt=ba.created_at.isoformat(),
    )


def _version_to_out(v: ConceptVersion) -> VersionOut:
    return VersionOut(
        id=v.id,
        projectId=v.project_id,
        briefAnalysisId=v.brief_analysis_id,
        name=v.name,
        floors=v.floors or ["Ground Floor"],
        blocks=v.blocks or [],
        overallScore=v.overall_score,
        programFitScore=v.program_fit_score,
        daylightScore=v.daylight_score,
        budgetFitScore=v.budget_fit_score,
        aiCommentary=v.ai_commentary,
        promotedRevisionId=v.promoted_revision_id,
        createdAt=v.created_at.isoformat(),
    )


def _suggestion_to_out(s: CopilotSuggestion) -> SuggestionOut:
    return SuggestionOut(
        id=s.id,
        projectId=s.project_id,
        category=s.category,
        text=s.text,
        priority=s.priority,
        status=s.status,
        createdAt=s.created_at.isoformat(),
    )


def _require_project(
    project_id: uuid.UUID, user: AuthUser, db: Session
) -> None:
    """Guard: raise 404 if the project doesn't exist in this org."""
    repo = SqlProjectRepository(db)
    if not repo.get(project_id, user.org_id):
        raise HTTPException(status_code=404, detail="Project not found")


# ---------------------------------------------------------------------------
# Brief analysis
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/analyze-brief",
    response_model=BriefAnalysisOut,
    status_code=status.HTTP_200_OK,
    summary="Analyze the project brief into a structured space program using AI",
)
def analyze_brief(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> BriefAnalysisOut:
    """Send the project's brief to Gemini and store the structured analysis.

    Re-running this endpoint creates a new BriefAnalysis record; earlier
    records are preserved for comparison.  The most recent record is always
    considered current.
    """
    _require_project(project_id, user, db)

    # Fetch the latest brief analysis to get the brief text, or fall back to
    # the project name if this is the first run.
    latest: BriefAnalysis | None = (
        db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )

    # Use existing brief text if available; callers can update brief via PATCH
    # on the project before re-running analysis.
    brief_text = (
        latest.brief_text
        if latest
        else "No brief text provided yet — please update the project brief."
    )

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable — set GEMINI_API_KEY in environment",
        )

    try:
        result = ai.analyze_brief(brief_text=brief_text)
    except Exception as exc:
        logger.error("Brief analysis failed for project %s: %s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    record = BriefAnalysis(
        project_id=project_id,
        brief_text=brief_text,
        summary=result.summary,
        space_program=result.space_program,
        constraints=result.constraints,
        opportunities=result.opportunities,
        open_questions=result.open_questions,
        provenance=result.provenance,
        model_version=result.model_version,
        created_by_user_id=user.user_id,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return _brief_analysis_to_out(record)


@router.post(
    "/projects/{project_id}/analyze-brief-with-text",
    response_model=BriefAnalysisOut,
    status_code=status.HTTP_200_OK,
    summary="Analyze a supplied brief text (does not require a prior brief on the project)",
)
def analyze_brief_with_text(
    project_id: uuid.UUID,
    body: dict[str, Any],
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> BriefAnalysisOut:
    """Accept raw brief text in the request body and run analysis."""
    _require_project(project_id, user, db)

    brief_text: str = body.get("clientBrief", "").strip()
    if not brief_text:
        raise HTTPException(status_code=422, detail="clientBrief must not be empty")

    project_context: dict[str, Any] = {
        k: body[k]
        for k in ("siteAddress", "siteSizeSqm", "budget", "stylePreferences")
        if k in body and body[k] is not None
    }

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable — set GEMINI_API_KEY in environment",
        )

    try:
        result = ai.analyze_brief(brief_text=brief_text, project_context=project_context)
    except Exception as exc:
        logger.error("Brief analysis failed for project %s: %s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    record = BriefAnalysis(
        project_id=project_id,
        brief_text=brief_text,
        summary=result.summary,
        space_program=result.space_program,
        constraints=result.constraints,
        opportunities=result.opportunities,
        open_questions=result.open_questions,
        provenance=result.provenance,
        model_version=result.model_version,
        created_by_user_id=user.user_id,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return _brief_analysis_to_out(record)


@router.get(
    "/projects/{project_id}/brief-analysis",
    response_model=BriefAnalysisOut | None,
    summary="Get the latest brief analysis for a project",
)
def get_brief_analysis(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> BriefAnalysisOut | None:
    _require_project(project_id, user, db)
    record: BriefAnalysis | None = (
        db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )
    return _brief_analysis_to_out(record) if record else None


# ---------------------------------------------------------------------------
# Concept versions (canvas snapshots)
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/versions",
    response_model=list[VersionOut],
    summary="List all concept canvas versions for a project",
)
def list_versions(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> list[VersionOut]:
    _require_project(project_id, user, db)
    versions = (
        db.query(ConceptVersion)
        .filter(ConceptVersion.project_id == project_id)
        .order_by(ConceptVersion.created_at.desc())
        .all()
    )
    return [_version_to_out(v) for v in versions]


@router.post(
    "/projects/{project_id}/versions",
    response_model=VersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new concept canvas version",
)
def create_version(
    project_id: uuid.UUID,
    body: VersionInput,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> VersionOut:
    _require_project(project_id, user, db)

    # Link to the latest brief analysis if one exists.
    latest_ba: BriefAnalysis | None = (
        db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )

    record = ConceptVersion(
        project_id=project_id,
        brief_analysis_id=latest_ba.id if latest_ba else None,
        name=body.name,
        floors=body.floors,
        blocks=[b.model_dump() for b in body.blocks],
        created_by_user_id=user.user_id,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return _version_to_out(record)


@router.get(
    "/versions/{version_id}",
    response_model=VersionOut,
    summary="Get a concept version by ID",
)
def get_version(
    version_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> VersionOut:
    v: ConceptVersion | None = db.get(ConceptVersion, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    # Org-isolation guard via project lookup.
    _require_project(v.project_id, user, db)
    return _version_to_out(v)


@router.delete(
    "/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a concept version",
)
def delete_version(
    version_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> None:
    v: ConceptVersion | None = db.get(ConceptVersion, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    _require_project(v.project_id, user, db)
    db.delete(v)


@router.post(
    "/versions/{version_id}/score",
    response_model=VersionOut,
    summary="Score a concept version against the project brief using AI",
)
def score_version(
    version_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> VersionOut:
    """Ask Gemini to score the version (0–100) across four dimensions:
    overall, program-fit, daylight, and budget-fit.
    Scores are written back to the ConceptVersion record.
    """
    v: ConceptVersion | None = db.get(ConceptVersion, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    _require_project(v.project_id, user, db)

    # Get the linked brief analysis (required for meaningful scoring).
    ba: BriefAnalysis | None = (
        db.get(BriefAnalysis, v.brief_analysis_id)
        if v.brief_analysis_id
        else db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == v.project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )

    if not ba:
        raise HTTPException(
            status_code=422,
            detail="Run analyze-brief before scoring a version — no brief analysis found",
        )

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable — set GEMINI_API_KEY in environment",
        )

    from services.ai.ai_service import BriefAnalysisResult

    ba_result = BriefAnalysisResult(
        summary=ba.summary,
        space_program=ba.space_program,
        constraints=ba.constraints,
        opportunities=ba.opportunities,
        open_questions=ba.open_questions,
        provenance=ba.provenance,
        model_version=ba.model_version,
    )

    version_data = {
        "id": str(v.id),
        "name": v.name,
        "floors": v.floors,
        "blocks": v.blocks,
    }

    try:
        result = ai.score_version(version_data=version_data, brief_analysis=ba_result)
    except Exception as exc:
        logger.error("Version scoring failed for %s: %s", version_id, exc)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    v.overall_score = float(result.overall_score)
    v.program_fit_score = float(result.program_fit)
    v.daylight_score = float(result.daylight)
    v.budget_fit_score = float(result.budget_fit)
    v.ai_commentary = result.commentary
    db.flush()
    db.refresh(v)
    return _version_to_out(v)


# ---------------------------------------------------------------------------
# Copilot suggestions
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/suggestions",
    response_model=list[SuggestionOut],
    summary="List copilot suggestions for a project",
)
def list_suggestions(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> list[SuggestionOut]:
    _require_project(project_id, user, db)
    suggestions = (
        db.query(CopilotSuggestion)
        .filter(CopilotSuggestion.project_id == project_id)
        .order_by(CopilotSuggestion.created_at.desc())
        .all()
    )
    return [_suggestion_to_out(s) for s in suggestions]


@router.post(
    "/projects/{project_id}/suggestions/generate",
    response_model=list[SuggestionOut],
    summary="Generate new AI suggestions for a project",
)
def generate_suggestions(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> list[SuggestionOut]:
    """Generate a fresh batch of categorized suggestions using Gemini (or the
    heuristic fallback).  Duplicate suggestions (matched by hash) are skipped
    so re-runs don't create noise.
    """
    _require_project(project_id, user, db)

    # Build project context for the AI.
    ba: BriefAnalysis | None = (
        db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )
    latest_version: ConceptVersion | None = (
        db.query(ConceptVersion)
        .filter(ConceptVersion.project_id == project_id)
        .order_by(ConceptVersion.created_at.desc())
        .first()
    )

    project_data: dict[str, Any] = {
        "id": str(project_id),
        "briefAnalysis": {
            "summary": ba.summary,
            "spaceProgram": ba.space_program,
            "constraints": ba.constraints,
        }
        if ba
        else {},
        "latestVersion": {
            "name": latest_version.name,
            "blocks": latest_version.blocks,
            "scores": {
                "overall": latest_version.overall_score,
                "programFit": latest_version.program_fit_score,
                "daylight": latest_version.daylight_score,
                "budgetFit": latest_version.budget_fit_score,
            },
        }
        if latest_version
        else {},
    }

    ai = get_ai_service()
    try:
        result = ai.generate_suggestions(project_data=project_data)
    except Exception as exc:
        logger.error("Suggestion generation failed for %s: %s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    # Collect existing hashes to skip duplicates.
    existing_hashes: set[str] = {
        s.suggestion_hash
        for s in db.query(CopilotSuggestion)
        .filter(CopilotSuggestion.project_id == project_id)
        .all()
        if s.suggestion_hash
    }

    created: list[CopilotSuggestion] = []
    for sug in result.suggestions:
        h = _suggestion_hash(sug.get("category", "general"), sug.get("text", ""))
        if h in existing_hashes:
            continue
        existing_hashes.add(h)
        record = CopilotSuggestion(
            project_id=project_id,
            category=sug.get("category", "general"),
            text=sug.get("text", ""),
            priority=sug.get("priority", "medium"),
            suggestion_hash=h,
            provenance=result.provenance,
            model_version=result.model_version,
        )
        db.add(record)
        created.append(record)

    if created:
        db.flush()
        for r in created:
            db.refresh(r)

    return [_suggestion_to_out(s) for s in created]


@router.patch(
    "/suggestions/{suggestion_id}",
    response_model=SuggestionOut,
    summary="Accept or dismiss a suggestion",
)
def update_suggestion(
    suggestion_id: uuid.UUID,
    body: SuggestionUpdate,
    user: AuthUser,
    _: Any = require_project_editor,
    db: Session = Depends(get_session),
) -> SuggestionOut:
    s: CopilotSuggestion | None = db.get(CopilotSuggestion, suggestion_id)
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    _require_project(s.project_id, user, db)
    s.status = body.status
    db.flush()
    db.refresh(s)
    return _suggestion_to_out(s)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/export",
    response_model=ProjectExportOut,
    summary="Export a full concept report as structured JSON with a Markdown narrative",
)
def export_project(
    project_id: uuid.UUID,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> ProjectExportOut:
    _require_project(project_id, user, db)

    ba: BriefAnalysis | None = (
        db.query(BriefAnalysis)
        .filter(BriefAnalysis.project_id == project_id)
        .order_by(BriefAnalysis.created_at.desc())
        .first()
    )

    # Best version = highest overall score, or most recent if none are scored.
    best: ConceptVersion | None = (
        db.query(ConceptVersion)
        .filter(
            ConceptVersion.project_id == project_id,
            ConceptVersion.overall_score.isnot(None),
        )
        .order_by(ConceptVersion.overall_score.desc())
        .first()
    )
    if not best:
        best = (
            db.query(ConceptVersion)
            .filter(ConceptVersion.project_id == project_id)
            .order_by(ConceptVersion.created_at.desc())
            .first()
        )

    markdown = _build_markdown(project_id, ba, best)

    return ProjectExportOut(
        projectId=project_id,
        briefAnalysis=_brief_analysis_to_out(ba) if ba else None,
        bestVersion=_version_to_out(best) if best else None,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        markdown=markdown,
    )


def _build_markdown(
    project_id: uuid.UUID,
    ba: BriefAnalysis | None,
    best: ConceptVersion | None,
) -> str:
    lines: list[str] = [f"# Concept Report — Project {project_id}\n"]

    if ba:
        lines.append("## Brief Analysis\n")
        lines.append(f"{ba.summary}\n")

        if ba.space_program:
            lines.append("### Space Program\n")
            lines.append("| Space | Area (sqm) | Priority | Notes |")
            lines.append("|---|---|---|---|")
            for item in ba.space_program:
                lines.append(
                    f"| {item.get('name','')} | {item.get('sqm','')} "
                    f"| {item.get('priority','')} | {item.get('notes') or ''} |"
                )
            lines.append("")

        if ba.constraints:
            lines.append("### Constraints\n")
            for c in ba.constraints:
                lines.append(f"- {c}")
            lines.append("")

        if ba.opportunities:
            lines.append("### Opportunities\n")
            for o in ba.opportunities:
                lines.append(f"- {o}")
            lines.append("")

        if ba.open_questions:
            lines.append("### Open Questions\n")
            for q in ba.open_questions:
                lines.append(f"- {q}")
            lines.append("")

    if best:
        lines.append(f"## Best Concept Version: {best.name}\n")
        if best.overall_score is not None:
            lines.append(
                f"**Scores** — Overall: {best.overall_score:.0f} / 100  "
                f"| Program fit: {best.program_fit_score:.0f}  "
                f"| Daylight: {best.daylight_score:.0f}  "
                f"| Budget fit: {best.budget_fit_score:.0f}\n"
            )
        if best.ai_commentary:
            lines.append(f"{best.ai_commentary}\n")

        if best.blocks:
            lines.append("### Canvas Zones\n")
            lines.append("| Zone | Type | Floor |")
            lines.append("|---|---|---|")
            for block in best.blocks:
                lines.append(
                    f"| {block.get('label','')} | {block.get('zoneType','')} "
                    f"| {block.get('floor','')} |"
                )
            lines.append("")

    lines.append(
        "\n---\n*This is a preliminary concept report. "
        "All geometry requires professional review before use in construction, "
        "permitting, or structural assessment.*"
    )
    return "\n".join(lines)
