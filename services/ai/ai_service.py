"""AI service for Advocate-Chambers - Gemini API integration.

This module provides AI-native features using Google's Gemini API:
- Brief analysis and space program generation
- Version scoring against briefs
- Proactive suggestion generation

All AI operations maintain proper validation, provenance tracking, and respect
the geometry-authority principle.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Optional Gemini SDK - degrade gracefully when not installed
try:
    from google import genai  # type: ignore[import]
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    genai = None  # type: ignore[assignment]

__all__ = ["AIService", "BriefAnalysisResult", "VersionScoreResult", "SuggestionResult", "get_ai_service", "_GEMINI_AVAILABLE"]


@dataclass
class BriefAnalysisResult:
    """Result of AI brief analysis."""
    summary: str
    space_program: list[dict[str, Any]]
    constraints: list[str]
    opportunities: list[str]
    open_questions: list[str]
    provenance: dict[str, Any] = field(default_factory=dict)
    model_version: str = "gemini-2.5-flash"


@dataclass
class VersionScoreResult:
    """Result of AI version scoring."""
    overall_score: int  # 0-100
    program_fit: int  # 0-100
    daylight: int  # 0-100
    budget_fit: int  # 0-100
    commentary: str
    zone_scores: list[dict[str, Any]]
    provenance: dict[str, Any] = field(default_factory=dict)
    model_version: str = "gemini-2.5-flash"


@dataclass
class SuggestionResult:
    """Result of AI suggestion generation."""
    suggestions: list[dict[str, Any]]
    categories: list[str]
    provenance: dict[str, Any] = field(default_factory=dict)
    model_version: str = "gemini-2.5-flash"


class AIService:
    """AI service for Advocate-Chambers using Gemini API."""
    
    def __init__(self) -> None:
        """Initialize AI service with Gemini API configuration."""
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        # Check availability at call-time so tests can mock the genai module
        sdk_present = genai is not None or _GEMINI_AVAILABLE
        self.available = sdk_present and bool(self.api_key)

        if self.available:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"AI service initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                self.available = False
        else:
            if not sdk_present:
                logger.warning("AI service unavailable: Gemini SDK not installed or API key missing")
            else:
                logger.warning("AI service unavailable: GEMINI_API_KEY not set")
    
    def analyze_brief(self, brief_text: str, project_context: dict[str, Any] | None = None) -> BriefAnalysisResult:
        """Analyze client brief and generate structured space program.
        
        Args:
            brief_text: Raw client brief text
            project_context: Optional project context (site size, budget, etc.)
            
        Returns:
            BriefAnalysisResult with structured analysis
            
        Raises:
            RuntimeError: If AI service is unavailable
        """
        if not self.available:
            raise RuntimeError("AI service unavailable - Gemini SDK not installed or API key missing")
        
        context = project_context or {}
        prompt = self._build_brief_analysis_prompt(brief_text, context)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Parse the structured response
            analysis = self._parse_brief_analysis(result_text)
            analysis.provenance = {
                "model": self.model_name,
                "timestamp": _get_timestamp(),
                "brief_length": len(brief_text),
                "context_keys": list(context.keys())
            }
            
            logger.info(f"Brief analysis completed with {len(analysis.space_program)} space program items")
            return analysis
            
        except Exception as e:
            logger.error(f"Brief analysis failed: {e}")
            raise RuntimeError(f"Brief analysis failed: {e}") from e
    
    def score_version(self, version_data: dict[str, Any], brief_analysis: BriefAnalysisResult) -> VersionScoreResult:
        """Score a design version against the brief analysis.
        
        Args:
            version_data: Version geometry and metadata
            brief_analysis: Previous brief analysis result
            
        Returns:
            VersionScoreResult with scores and commentary
            
        Raises:
            RuntimeError: If AI service is unavailable
        """
        if not self.available:
            raise RuntimeError("AI service unavailable - Gemini SDK not installed or API key missing")
        
        prompt = self._build_version_scoring_prompt(version_data, brief_analysis)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Parse the scoring response
            scoring = self._parse_version_scoring(result_text)
            scoring.provenance = {
                "model": self.model_name,
                "timestamp": _get_timestamp(),
                "version_id": version_data.get("id"),
                "brief_analysis_id": brief_analysis.provenance.get("timestamp")
            }
            
            logger.info(f"Version scoring completed: overall={scoring.overall_score}")
            return scoring
            
        except Exception as e:
            logger.error(f"Version scoring failed: {e}")
            raise RuntimeError(f"Version scoring failed: {e}") from e
    
    def generate_suggestions(self, project_data: dict[str, Any], categories: list[str] | None = None) -> SuggestionResult:
        """Generate proactive design suggestions.
        
        Args:
            project_data: Project brief, version, and context data
            categories: Optional list of suggestion categories to generate
            
        Returns:
            SuggestionResult with categorized suggestions
            
        Raises:
            RuntimeError: If AI service is unavailable
        """
        if not self.available:
            raise RuntimeError("AI service unavailable - Gemini SDK not installed or API key missing")
        
        target_categories = categories or ["program", "site", "daylight", "budget", "circulation", "general"]
        prompt = self._build_suggestions_prompt(project_data, target_categories)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Parse the suggestions response
            suggestions = self._parse_suggestions(result_text)
            suggestions.categories = target_categories
            suggestions.provenance = {
                "model": self.model_name,
                "timestamp": _get_timestamp(),
                "project_id": project_data.get("id"),
                "categories_requested": target_categories
            }
            
            logger.info(f"Suggestions generated: {len(suggestions.suggestions)} across {len(target_categories)} categories")
            return suggestions
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            raise RuntimeError(f"Suggestion generation failed: {e}") from e
    
    def _build_brief_analysis_prompt(self, brief_text: str, context: dict[str, Any]) -> str:
        """Build prompt for brief analysis."""
        context_str = json.dumps(context, indent=2) if context else "No additional context"
        
        return f"""You are an architectural analysis assistant. Analyze the following client brief and provide a structured response.

CLIENT BRIEF:
{brief_text}

ADDITIONAL CONTEXT:
{context_str}

Provide your response in the following JSON format:
{{
  "summary": "Brief summary of the project",
  "spaceProgram": [
    {{
      "name": "Living Room",
      "sqm": 45,
      "priority": "must-have",
      "notes": "Primary gathering space, needs good natural light"
    }}
  ],
  "constraints": ["Site constraint 1", "Budget constraint 2"],
  "opportunities": ["Design opportunity 1", "Site opportunity 2"],
  "openQuestions": ["Question for client 1", "Clarification needed 2"]
}}

Focus on extracting realistic space requirements, identifying constraints, and highlighting design opportunities."""
    
    def _build_version_scoring_prompt(self, version_data: dict[str, Any], brief_analysis: BriefAnalysisResult) -> str:
        """Build prompt for version scoring."""
        version_str = json.dumps(version_data, indent=2)
        brief_str = json.dumps({
            "summary": brief_analysis.summary,
            "spaceProgram": brief_analysis.space_program,
            "constraints": brief_analysis.constraints
        }, indent=2)
        
        return f"""You are an architectural evaluation assistant. Score the following design version against the brief analysis.

DESIGN VERSION:
{version_str}

BRIEF ANALYSIS:
{brief_str}

Provide your response in the following JSON format:
{{
  "overallScore": 85,
  "programFit": 90,
  "daylight": 75,
  "budgetFit": 80,
  "commentary": "Overall assessment of the design",
  "zoneScores": [
    {{
      "zoneName": "Living Room",
      "score": 85,
      "notes": "Good size, could improve daylight"
    }}
  ]
}}

Score each aspect on a 0-100 scale based on how well the design meets the brief requirements."""
    
    def _build_suggestions_prompt(self, project_data: dict[str, Any], categories: list[str]) -> str:
        """Build prompt for suggestion generation."""
        project_str = json.dumps(project_data, indent=2)
        categories_str = ", ".join(categories)
        
        return f"""You are an architectural design assistant. Generate proactive suggestions for the following project.

PROJECT DATA:
{project_str}

SUGGESTION CATEGORIES: {categories_str}

Provide your response in the following JSON format:
{{
  "suggestions": [
    {{
      "category": "program",
      "text": "Consider expanding the kitchen to improve workflow",
      "priority": "medium"
    }}
  ]
}}

Generate 2-3 suggestions per category if applicable. Focus on practical, implementable improvements."""
    
    def _parse_brief_analysis(self, result_text: str) -> BriefAnalysisResult:
        """Parse brief analysis response from AI."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json(result_text)
            data = json.loads(json_str)
            
            return BriefAnalysisResult(
                summary=data.get("summary", ""),
                space_program=data.get("spaceProgram", []),
                constraints=data.get("constraints", []),
                opportunities=data.get("opportunities", []),
                open_questions=data.get("openQuestions", [])
            )
        except Exception as e:
            logger.error(f"Failed to parse brief analysis: {e}")
            # Return a minimal valid result on parse failure
            return BriefAnalysisResult(
                summary="Analysis parsing failed",
                space_program=[],
                constraints=[],
                opportunities=[],
                open_questions=["Unable to parse AI response"]
            )
    
    def _parse_version_scoring(self, result_text: str) -> VersionScoreResult:
        """Parse version scoring response from AI."""
        try:
            json_str = self._extract_json(result_text)
            data = json.loads(json_str)
            
            return VersionScoreResult(
                overall_score=data.get("overallScore", 50),
                program_fit=data.get("programFit", 50),
                daylight=data.get("daylight", 50),
                budget_fit=data.get("budgetFit", 50),
                commentary=data.get("commentary", ""),
                zone_scores=data.get("zoneScores", [])
            )
        except Exception as e:
            logger.error(f"Failed to parse version scoring: {e}")
            return VersionScoreResult(
                overall_score=50,
                program_fit=50,
                daylight=50,
                budget_fit=50,
                commentary="Scoring parsing failed",
                zone_scores=[]
            )
    
    def _parse_suggestions(self, result_text: str) -> SuggestionResult:
        """Parse suggestions response from AI."""
        try:
            json_str = self._extract_json(result_text)
            data = json.loads(json_str)
            
            return SuggestionResult(
                suggestions=data.get("suggestions", []),
                categories=[]
            )
        except Exception as e:
            logger.error(f"Failed to parse suggestions: {e}")
            return SuggestionResult(
                suggestions=[],
                categories=[]
            )
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text, handling markdown code blocks."""
        # Try to find JSON between ```json and ``` markers
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # Try to find JSON between ``` and ``` markers
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # Return as-is if no markdown markers found
        return text.strip()


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# Global AI service instance
_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    """Get or create the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service