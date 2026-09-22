"""AI analysis routes for Advocate-Chambers API.

Provides endpoints for AI-native features:
- Brief analysis using Gemini API
- Version scoring against briefs
- Proactive suggestion generation

All AI operations maintain proper validation, provenance tracking, and respect
the geometry-authority principle.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.ai.ai_service import (
    AIService,
    BriefAnalysisResult,
    SuggestionResult,
    VersionScoreResult,
    get_ai_service,
)
from services.api.auth import AuthUser, get_current_user
from services.api.authorization import require_project_viewer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


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


@router.post("/generate-suggestions", response_model=SuggestionsResponse)
def generate_suggestions(
    request: SuggestionsRequest,
    user: AuthUser,
    _: Any = require_project_viewer,
) -> SuggestionsResponse:
    """Generate proactive design suggestions using AI.
    
    This endpoint generates categorized suggestions for design improvements
    based on the project brief, version, and context data.
    """
    try:
        ai_service = get_ai_service()
        
        if not ai_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable - Gemini SDK not installed or API key missing"
            )
        
        result = ai_service.generate_suggestions(
            project_data=request.project_data,
            categories=request.categories
        )
        
        return SuggestionsResponse(
            version="ai-suggestions.v1",
            suggestions=result.suggestions,
            categories=result.categories,
            provenance=result.provenance,
            model_version=result.model_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestion generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suggestion generation failed: {str(e)}"
        ) from e


@router.get("/health")
def ai_health() -> dict[str, Any]:
    """Health check for AI service."""
    # Check if Gemini SDK is available
    gemini_available = False
    try:
        from google import genai  # type: ignore[import]
        gemini_available = True
    except ImportError:
        pass
    
    ai_service = get_ai_service()
    
    return {
        "status": "available" if ai_service.available else "unavailable",
        "model": ai_service.model_name if ai_service.available else None,
        "sdk_installed": gemini_available
    }