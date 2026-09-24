"""AI analysis routes for Advocate-Chambers API.

Provides endpoints for AI-native features:
- Brief analysis using Gemini API
- Version scoring against briefs (Phase 14)
- Proactive suggestion generation (Phase 14)
- Multi-version tradeoff comparison (Phase 16)
- Quality-gate scoring track (Phase 16)

All AI operations maintain proper validation, provenance tracking, and respect
the geometry-authority principle.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.ai.ai_service import (
    AIService,
    BriefAnalysisResult,
    SuggestionResult,
    VersionScoreResult,
    get_ai_service,
)
from services.api.auth import AuthUser, get_current_user
from services.api.authorization import require_project_viewer
from services.api.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Lazy import to avoid circular dependency when Phase 16 module isn't present
def _get_scoring_engine() -> Any:
    try:
        from scripts.phase16_ai_scoring import VersionScoringEngine
        return VersionScoringEngine()
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class BriefAnalysisRequest(BaseModel):
    """Request for AI brief analysis."""
    
    brief_text: str = Field(..., description="Raw client brief text")
    project_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional project context (site size, budget, etc.)"
    )


class BriefAnalysisResponse(BaseModel):
    """Response from AI brief analysis."""
    
    version: str
    summary: str
    space_program: list[dict[str, Any]]
    constraints: list[str]
    opportunities: list[str]
    open_questions: list[str]
    provenance: dict[str, Any]
    model_version: str


class VersionScoreRequest(BaseModel):
    """Request for AI version scoring."""
    
    version_data: dict[str, Any] = Field(..., description="Version geometry and metadata")
    brief_analysis: BriefAnalysisResponse = Field(..., description="Brief analysis to score against")


class RevisionScoreRequest(BaseModel):
    """Request for AI revision scoring (Phase 16A enhancement)."""
    
    revision_id: uuid.UUID = Field(..., description="Revision ID to score")
    brief_analysis_id: str | None = Field(None, description="Brief analysis ID (uses latest if not provided)")


class VersionScoreResponse(BaseModel):
    """Response from AI version scoring."""
    
    version: str
    overall_score: int
    program_fit: int
    daylight: int
    budget_fit: int
    commentary: str
    zone_scores: list[dict[str, Any]]
    provenance: dict[str, Any]
    model_version: str


class SuggestionsRequest(BaseModel):
    """Request for AI suggestion generation."""
    
    project_data: dict[str, Any] = Field(..., description="Project brief, version, and context data")
    categories: list[str] | None = Field(
        default=None,
        description="Optional list of suggestion categories to generate"
    )


class SuggestionsResponse(BaseModel):
    """Response from AI suggestion generation."""
    
    version: str
    suggestions: list[dict[str, Any]]
    categories: list[str]
    provenance: dict[str, Any]
    model_version: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/analyze-brief", response_model=BriefAnalysisResponse)
def analyze_brief(
    request: BriefAnalysisRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
) -> BriefAnalysisResponse:
    """Analyze client brief using AI and generate structured space program.
    
    This endpoint sends the raw client brief to the AI service (Gemini API)
    and returns a structured analysis including space program, constraints,
    opportunities, and open questions.
    
    The AI service degrades gracefully if the Gemini SDK is not installed
    or if the API key is not configured.
    """
    try:
        ai_service = get_ai_service()
        
        if not ai_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable - Gemini SDK not installed or API key missing"
            )
        
        result = ai_service.analyze_brief(
            brief_text=request.brief_text,
            project_context=request.project_context
        )
        
        return BriefAnalysisResponse(
            version="ai-brief-analysis.v1",
            summary=result.summary,
            space_program=result.space_program,
            constraints=result.constraints,
            opportunities=result.opportunities,
            open_questions=result.open_questions,
            provenance=result.provenance,
            model_version=result.model_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brief analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Brief analysis failed: {str(e)}"
        ) from e


@router.post("/score-version", response_model=VersionScoreResponse)
def score_version(
    request: VersionScoreRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
) -> VersionScoreResponse:
    """Score a design version against the brief using AI.
    
    This endpoint evaluates a design version against the brief analysis
    and returns scores for overall fit, program fit, daylight, and budget fit,
    along with written commentary and per-zone scores.
    """
    try:
        ai_service = get_ai_service()
        
        if not ai_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable - Gemini SDK not installed or API key missing"
            )
        
        # Convert Pydantic response to internal dataclass
        brief_analysis_result = BriefAnalysisResult(
            summary=request.brief_analysis.summary,
            space_program=request.brief_analysis.space_program,
            constraints=request.brief_analysis.constraints,
            opportunities=request.brief_analysis.opportunities,
            open_questions=request.brief_analysis.open_questions,
            provenance=request.brief_analysis.provenance,
            model_version=request.brief_analysis.model_version
        )
        
        result = ai_service.score_version(
            version_data=request.version_data,
            brief_analysis=brief_analysis_result
        )
        
        return VersionScoreResponse(
            version="ai-version-score.v1",
            overall_score=result.overall_score,
            program_fit=result.program_fit,
            daylight=result.daylight,
            budget_fit=result.budget_fit,
            commentary=result.commentary,
            zone_scores=result.zone_scores,
            provenance=result.provenance,
            model_version=result.model_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Version scoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Version scoring failed: {str(e)}"
        ) from e


@router.post("/score-revision/{project_id}", response_model=VersionScoreResponse)
def score_revision(
    project_id: uuid.UUID,
    request: RevisionScoreRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
    db: Session = Depends(get_session),
) -> VersionScoreResponse:
    """Score a specific revision against the brief using AI (Phase 16A enhancement).
    
    This endpoint is a convenience wrapper that fetches the revision data,
    retrieves or creates brief analysis, and scores the revision in one call.
    This is designed for frontend integration where revision IDs are readily available.
    """
    from services.api.models.orm import Revision, Project, ScoringResult
    
    try:
        ai_service = get_ai_service()
        
        if not ai_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable - Gemini SDK not installed or API key missing"
            )
        
        pid = uuid.UUID(str(project_id))
        rid = uuid.UUID(str(request.revision_id))

        project = db.query(Project).filter(Project.id == pid).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        revision = db.query(Revision).filter(
            Revision.id == rid,
            Revision.project_id == pid
        ).first()
        
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revision not found"
            )
        
        existing_scoring = db.query(ScoringResult).filter(
            ScoringResult.revision_id == rid
        ).first()
        
        if existing_scoring:
            logger.info(f"Returning existing scoring for revision {request.revision_id}")
            return VersionScoreResponse(
                version="ai-version-score.v1",
                overall_score=existing_scoring.overall_score,
                program_fit=existing_scoring.program_fit,
                daylight=existing_scoring.daylight_score,
                budget_fit=existing_scoring.budget_fit,
                commentary=existing_scoring.commentary,
                zone_scores=existing_scoring.zone_scores,
                provenance=existing_scoring.provenance,
                model_version=existing_scoring.model_version
            )
        
        brief_text = "Client brief for project"
        
        brief_analysis_result = ai_service.analyze_brief(
            brief_text=brief_text,
            project_context={
                "projectId": str(project_id),
                "revisionId": str(request.revision_id),
            }
        )
        
        version_data = {
            "id": str(revision.id),
            "revisionNumber": revision.revision_number,
            "validationState": revision.validation_state,
            "metadata": {
                "authorUserId": str(revision.author_user_id) if revision.author_user_id else None,
                "reason": revision.reason,
                "engineVersion": revision.engine_version,
            },
        }
        
        result = ai_service.score_version(
            version_data=version_data,
            brief_analysis=brief_analysis_result
        )
        
        scoring_record = ScoringResult(
            project_id=pid,
            revision_id=rid,
            brief_analysis_id=brief_analysis_result.provenance.get("timestamp"),
            overall_score=result.overall_score,
            program_fit=result.program_fit,
            daylight_score=result.daylight,
            budget_fit=result.budget_fit,
            commentary=result.commentary,
            zone_scores=result.zone_scores,
            provenance=result.provenance,
            model_version=result.model_version,
            created_by_user_id=user.user_id,
        )
        
        db.add(scoring_record)
        
        logger.info(f"Created scoring result for revision {request.revision_id}")
        
        return VersionScoreResponse(
            version="ai-version-score.v1",
            overall_score=result.overall_score,
            program_fit=result.program_fit,
            daylight=result.daylight,
            budget_fit=result.budget_fit,
            commentary=result.commentary,
            zone_scores=result.zone_scores,
            provenance=result.provenance,
            model_version=result.model_version,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revision scoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revision scoring failed: {str(e)}"
        ) from e


@router.post("/generate-suggestions", response_model=SuggestionsResponse)
def generate_suggestions(
    request: SuggestionsRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
) -> SuggestionsResponse:
    """Generate proactive design suggestions with heuristic fallback (Phase 17).

    Uses Gemini when available; degrades transparently to the deterministic
    :class:`HeuristicSuggestionEngine` when the SDK/key are absent or when
    the remote call fails.  Suggestions are always returned in a uniform
    schema carrying category, priority, text, SHA-256 hash and provenance.

    The returned objects match the ``ai-suggestions.v1`` schema documented
    in :ref:`Phase 17 <docs/IMPLEMENTATION_PLAN.md>`.
    """
    try:
        ai_service = get_ai_service()

        result = ai_service.generate_suggestions(
            project_data=request.project_data,
            categories=request.categories,
        )

        return SuggestionsResponse(
            version="ai-suggestions.v1",
            suggestions=result.suggestions,
            categories=result.categories,
            provenance=result.provenance,
            model_version=result.model_version,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestion generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suggestion generation failed: {str(e)}"
        ) from e


# ---------------------------------------------------------------------------
# Phase 16 — Multi-version comparison & quality gate scoring
# ---------------------------------------------------------------------------


class VersionCompareRequest(BaseModel):
    """Request to compare multiple design versions."""

    versions: list[dict[str, Any]] = Field(
        ..., description="List of version dicts (id, totalArea, estimatedCost, zones)"
    )
    brief: dict[str, Any] = Field(
        ..., description="Project brief dict (spaceProgram, maxBudget, constraints)"
    )
    minimum_score: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum overall score required for quality gate PASS",
    )


class VersionCompareResponse(BaseModel):
    """Response for multi-version tradeoff comparison."""

    schema_version: str
    generated_at: str
    version_count: int
    winner: str | None
    tradeoff_notes: list[str]
    matrix: list[dict[str, Any]]
    quality_gate_track: dict[str, Any]


@router.post("/compare-versions", response_model=VersionCompareResponse)
def compare_versions(
    request: VersionCompareRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
) -> VersionCompareResponse:
    """Compare multiple design versions and return a tradeoff matrix (Phase 16).

    Scores each version using the Phase 16 heuristic/Gemini engine, selects the
    best version, and returns a tradeoff analysis.  Also returns a quality gate
    track dict suitable for integration into ``build_quality_gate()``.
    """
    engine = _get_scoring_engine()
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phase 16 scoring engine not available",
        )

    try:
        comparison = engine.compare_versions(request.versions, request.brief)
        gate_track = engine.score_for_quality_gate(
            request.versions, request.brief, minimum_score=request.minimum_score
        )
        d = comparison.to_dict()
        return VersionCompareResponse(
            schema_version=d["schemaVersion"],
            generated_at=d["generatedAt"],
            version_count=d["versionCount"],
            winner=d["winner"],
            tradeoff_notes=d["tradeoffNotes"],
            matrix=d["matrix"],
            quality_gate_track=gate_track,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Version comparison failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Version comparison failed: {e}",
        ) from e


@router.get("/health")
def ai_health() -> dict[str, Any]:
    """Health check for AI service and Phase 16 scoring engine."""
    gemini_available = False
    try:
        from google import genai  # type: ignore[import]
        gemini_available = True
    except ImportError:
        pass

    ai_service = get_ai_service()
    scoring_engine_available = _get_scoring_engine() is not None

    return {
        "status": "available" if ai_service.available else "unavailable",
        "model": ai_service.model_name if ai_service.available else None,
        "sdk_installed": gemini_available,
        "phase16_scoring_engine": scoring_engine_available,
    }