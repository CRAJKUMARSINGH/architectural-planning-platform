"""Phase 14 — AI Brief Analysis Integration regression tests.

Tests validate the AI brief analysis integration:
- AI service initialization and graceful degradation
- Brief analysis schema validation
- API route functionality with proper error handling
- Integration with existing Week 11-12 pipeline
- Quality gate integration for AI-generated content
- Provenance tracking for AI operations

These tests run without a live Gemini API key or SDK.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures" / "phase14"


class Phase14SchemaTests(unittest.TestCase):
    """AI brief analysis schema validation tests."""
    
    def test_ai_brief_analysis_schema_exists(self) -> None:
        """AI brief analysis schema file exists and is valid JSON."""
        schema_path = ROOT / "packages" / "schema" / "ai-brief-analysis.schema.json"
        self.assertTrue(schema_path.exists())
        
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["version"], "ai-brief-analysis.v1")
        self.assertIn("spaceProgram", schema["required"])
        self.assertIn("provenance", schema["required"])
    
    def test_ai_version_score_schema_exists(self) -> None:
        """AI version score schema file exists and is valid JSON."""
        schema_path = ROOT / "packages" / "schema" / "ai-version-score.schema.json"
        self.assertTrue(schema_path.exists())
        
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["version"], "ai-version-score.v1")
        self.assertIn("overallScore", schema["required"])
        self.assertIn("provenance", schema["required"])
    
    def test_ai_suggestions_schema_exists(self) -> None:
        """AI suggestions schema file exists and is valid JSON."""
        schema_path = ROOT / "packages" / "schema" / "ai-suggestions.schema.json"
        self.assertTrue(schema_path.exists())
        
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["version"], "ai-suggestions.v1")
        self.assertIn("suggestions", schema["required"])
        self.assertIn("provenance", schema["required"])


class Phase14AIServiceTests(unittest.TestCase):
    """AI service initialization and degradation tests."""
    
    def test_ai_service_initializes_without_gemini(self) -> None:
        """AI service degrades gracefully when Gemini SDK is not installed."""
        from services.ai.ai_service import AIService
        
        # Temporarily remove Gemini from sys.modules if present
        gemini_module = sys.modules.pop("google.genai", None)
        original_available = sys.modules.pop("services.ai.ai_service._GEMINI_AVAILABLE", None)
        
        try:
            # Ensure API key is not set
            original_key = os.environ.pop("GEMINI_API_KEY", None)
            
            service = AIService()
            self.assertFalse(service.available)
            self.assertIsNone(service.api_key)
            
        finally:
            # Restore environment
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
            if gemini_module:
                sys.modules["google.genai"] = gemini_module
            if original_available:
                sys.modules["services.ai.ai_service._GEMINI_AVAILABLE"] = original_available
    
    def test_ai_service_requires_api_key(self) -> None:
        """AI service requires API key to be available."""
        from services.ai.ai_service import AIService
        
        original_key = os.environ.pop("GEMINI_API_KEY", None)
        
        try:
            service = AIService()
            self.assertFalse(service.available)
        finally:
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
    
    def test_ai_service_initializes_with_key(self) -> None:
        """AI service initializes when API key is present (with mock)."""
        from services.ai.ai_service import AIService
        
        original_key = os.environ.get("GEMINI_API_KEY")
        
        try:
            os.environ["GEMINI_API_KEY"] = "test-key-123"
            
            # Mock the Gemini SDK to avoid actual API calls
            with patch("services.ai.ai_service.genai") as mock_genai:
                mock_model = MagicMock()
                mock_genai.configure.return_value = None
                mock_genai.GenerativeModel.return_value = mock_model
                
                service = AIService()
                self.assertTrue(service.available)
                self.assertEqual(service.api_key, "test-key-123")
                
        finally:
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key
            else:
                os.environ.pop("GEMINI_API_KEY", None)


class Phase14RouteTests(unittest.TestCase):
    """AI API route tests."""
    
    def test_ai_routes_file_exists(self) -> None:
        """AI routes file exists."""
        routes_path = ROOT / "services" / "api" / "routes" / "v1_ai.py"
        self.assertTrue(routes_path.exists())
    
    def test_ai_routes_importable(self) -> None:
        """AI routes can be imported without errors."""
        try:
            from services.api.routes import v1_ai
            self.assertIsNotNone(v1_ai)
        except ImportError as e:
            self.fail(f"Failed to import AI routes: {e}")
    
    def test_ai_health_endpoint_defined(self) -> None:
        """AI health endpoint is defined."""
        from services.api.routes import v1_ai
        
        # Check that the health function exists
        self.assertTrue(hasattr(v1_ai, "ai_health"))
    
    def test_ai_analyze_brief_endpoint_defined(self) -> None:
        """AI brief analysis endpoint is defined."""
        from services.api.routes import v1_ai
        
        # Check that the analyze_brief function exists
        self.assertTrue(hasattr(v1_ai, "analyze_brief"))
    
    def test_ai_score_version_endpoint_defined(self) -> None:
        """AI version scoring endpoint is defined."""
        from services.api.routes import v1_ai
        
        # Check that the score_version function exists
        self.assertTrue(hasattr(v1_ai, "score_version"))
    
    def test_ai_generate_suggestions_endpoint_defined(self) -> None:
        """AI suggestion generation endpoint is defined."""
        from services.api.routes import v1_ai
        
        # Check that the generate_suggestions function exists
        self.assertTrue(hasattr(v1_ai, "generate_suggestions"))


class Phase14IntegrationTests(unittest.TestCase):
    """Integration tests with existing Week 11-12 pipeline."""
    
    def test_week1112_scripts_exist(self) -> None:
        """Week 11-12 scripts exist for integration."""
        week1112_script = ROOT / "scripts" / "week1112.py"
        self.assertTrue(week1112_script.exists())
    
    def test_ai_service_can_be_imported_by_week1112(self) -> None:
        """AI service can be imported by Week 11-12 scripts."""
        try:
            from services.ai.ai_service import get_ai_service
            self.assertIsNotNone(get_ai_service)
        except ImportError as e:
            self.fail(f"Failed to import AI service: {e}")
    
    def test_ai_brief_analysis_schema_versioned(self) -> None:
        """AI brief analysis schema uses proper versioning."""
        schema_path = ROOT / "packages" / "schema" / "ai-brief-analysis.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        
        self.assertEqual(schema["version"], "ai-brief-analysis.v1")
        self.assertIn("$id", schema)
        self.assertIn("$schema", schema)


class Phase14QualityGateTests(unittest.TestCase):
    """Quality gate integration tests for AI-generated content."""
    
    def test_ai_provenance_tracking_fields(self) -> None:
        """AI provenance includes required tracking fields."""
        schema_path = ROOT / "packages" / "schema" / "ai-brief-analysis.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        
        provenance_props = schema["properties"]["provenance"]["properties"]
        self.assertIn("model", provenance_props)
        self.assertIn("timestamp", provenance_props)
        self.assertIn("briefLength", provenance_props)
    
    def test_ai_content_marked_as_ai_generated(self) -> None:
        """AI-generated content includes model version identifier."""
        schema_path = ROOT / "packages" / "schema" / "ai-brief-analysis.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        
        self.assertIn("modelVersion", schema["required"])
        self.assertEqual(schema["properties"]["modelVersion"]["type"], "string")


if __name__ == "__main__":
    unittest.main()