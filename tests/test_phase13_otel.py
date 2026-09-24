"""Phase 13 — OpenTelemetry export configuration and span context regressions.

Tests validate the locally-testable portions of the OTel integration:
- OtelConfig dataclass (env-driven, graceful degradation)
- pipeline_span context manager (timing, error capture, attribute recording)
- SpanContext bridge (correlation ID promotion)
- OtelJsonFormatter (structured JSON, sensitive-key stripping)
- MEASURED_STAGES completeness against the contract fixture

These tests run without a collector or the OTel SDK installed.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase13" / "otel_contract.json"

from services.api.middleware.telemetry import (  # noqa: E402
    MEASURED_STAGES,
    OtelConfig,
    OtelJsonFormatter,
    SpanContext,
    pipeline_span,
)


class Phase13OtelConfigTests(unittest.TestCase):
    """OtelConfig env-driven configuration."""

    def test_fixture_integrity(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(fixture["version"], "phase13.otel-contract.v1")
        self.assertEqual(len(fixture["measuredStages"]), 10)
        for key in fixture["configKeys"]:
            self.assertIn(key, {"endpoint", "serviceName", "insecure",
                                 "sdkAvailable", "exporterAvailable", "exportEnabled"})

    def test_measured_stages_match_contract(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(list(MEASURED_STAGES), fixture["measuredStages"])

    def test_config_from_env_no_endpoint(self) -> None:
        """Without OTEL_EXPORTER_OTLP_ENDPOINT export is disabled."""
        env = {k: v for k, v in os.environ.items()
               if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
        original = os.environ.copy()
        try:
            os.environ.clear()
            os.environ.update(env)
            os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
            config = OtelConfig.from_env()
            self.assertIsNone(config.endpoint)
            self.assertFalse(config.is_export_enabled)
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_config_from_env_with_endpoint(self) -> None:
        """When endpoint is set, config reflects it."""
        original = os.environ.copy()
        try:
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
            os.environ["OTEL_SERVICE_NAME"] = "advocate-test"
            os.environ["OTEL_EXPORTER_OTLP_INSECURE"] = "true"
            config = OtelConfig.from_env()
            self.assertEqual(config.endpoint, "http://localhost:4317")
            self.assertEqual(config.service_name, "advocate-test")
            self.assertTrue(config.insecure)
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_config_to_dict_has_all_contract_keys(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        config = OtelConfig.from_env()
        d = config.to_dict()
        for key in fixture["configKeys"]:
            # Convert camelCase fixture keys to match to_dict output
            self.assertIn(key, d, f"Missing key: {key}")

    def test_default_service_name(self) -> None:
        original = os.environ.copy()
        try:
            os.environ.pop("OTEL_SERVICE_NAME", None)
            config = OtelConfig.from_env()
            self.assertEqual(config.service_name, "architectural-planning-platform-api")
        finally:
            os.environ.clear()
            os.environ.update(original)


class Phase13SpanContextTests(unittest.TestCase):
    """SpanContext bridge and pipeline_span context manager."""

    def test_span_context_fields_match_contract(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        span = SpanContext(
            stage="quick_validation",
            trace_id="trace-abc",
            request_id="req-123",
            revision_id="rev-5",
            org_id="org-1",
        )
        span.finish()
        d = span.to_dict()
        for field in fixture["spanContextFields"]:
            self.assertIn(field, d, f"Missing field: {field}")

    def test_pipeline_span_records_elapsed(self) -> None:
        with pipeline_span("quick_validation", {"trace_id": "t1", "request_id": "r1"}) as span:
            pass
        self.assertGreaterEqual(span.elapsed_seconds, 0.0)
        self.assertIsNone(span.error)

    def test_pipeline_span_captures_error(self) -> None:
        with self.assertRaises(ValueError):
            with pipeline_span("full_validation") as span:
                raise ValueError("bad model")
        self.assertIsNotNone(span.error)
        self.assertIn("bad model", span.error)

    def test_pipeline_span_custom_attributes(self) -> None:
        with pipeline_span("revision_creation", extra_attributes={"revision_number": 42}) as span:
            span.attributes["finding_count"] = 3
        self.assertEqual(span.attributes["revision_number"], 42)
        self.assertEqual(span.attributes["finding_count"], 3)

    def test_pipeline_span_all_ten_stages_are_valid(self) -> None:
        """Each measured stage name can be used in pipeline_span without error."""
        for stage in MEASURED_STAGES:
            with pipeline_span(stage) as span:
                pass
            self.assertEqual(span.stage, stage)

    def test_span_context_correlation_ids_propagate(self) -> None:
        correlation = {
            "trace_id": "trace-xyz",
            "request_id": "req-abc",
            "revision_id": "rev-7",
            "org_id": "org-5",
        }
        with pipeline_span("dxf_export", correlation) as span:
            pass
        self.assertEqual(span.trace_id, "trace-xyz")
        self.assertEqual(span.request_id, "req-abc")
        self.assertEqual(span.revision_id, "rev-7")
        self.assertEqual(span.org_id, "org-5")

    def test_span_elapsed_never_negative(self) -> None:
        span = SpanContext(stage="pdf_export")
        span.finish()
        self.assertGreaterEqual(span.elapsed_seconds, 0.0)

    def test_span_to_dict_elapsed_rounded(self) -> None:
        span = SpanContext(stage="artifact_upload")
        span.finish()
        d = span.to_dict()
        # round() with 6 places returns a float — check it's present
        self.assertIsInstance(d["elapsedSeconds"], float)


class Phase13OtelJsonFormatterTests(unittest.TestCase):
    """OtelJsonFormatter emits valid JSON and strips sensitive keys."""

    def _format_record(self, message: str, extra: dict | None = None) -> dict:
        formatter = OtelJsonFormatter()
        record = logging.LogRecord(
            name="advocate.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        if extra:
            for k, v in extra.items():
                setattr(record, k, v)
        line = formatter.format(record)
        return json.loads(line)

    def test_output_is_valid_json(self) -> None:
        d = self._format_record("hello world")
        self.assertIsInstance(d, dict)

    def test_required_fields_present(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        d = self._format_record("test event")
        for f in fixture["logFormatterFields"]:
            self.assertIn(f, d, f"Missing formatter field: {f}")

    def test_otel_extra_fields_are_included(self) -> None:
        d = self._format_record(
            "pipeline event",
            extra={"otel": {"traceId": "t123", "stage": "quick_validation"}},
        )
        self.assertEqual(d["traceId"], "t123")
        self.assertEqual(d["stage"], "quick_validation")

    def test_sensitive_keys_are_stripped(self) -> None:
        d = self._format_record(
            "auth event",
            extra={"otel": {
                "authorization": "Bearer secret",
                "cookie": "session=abc",
                "password": "hunter2",
                "token": "tok",
                "stage": "brief_compilation",
            }},
        )
        self.assertNotIn("authorization", d)
        self.assertNotIn("cookie", d)
        self.assertNotIn("password", d)
        self.assertNotIn("token", d)
        self.assertIn("stage", d)

    def test_severity_is_levelname(self) -> None:
        d = self._format_record("warning event")
        self.assertEqual(d["severity"], "INFO")

    def test_timestamp_is_iso8601(self) -> None:
        from datetime import datetime, timezone
        d = self._format_record("ts test")
        # Should parse without error
        parsed = datetime.fromisoformat(d["timestamp"])
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_security_rules_documented_in_fixture(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        rules_text = " ".join(fixture["securityRules"]).lower()
        self.assertIn("authorization", rules_text)
        self.assertIn("environment", rules_text)
        self.assertIn("degrade", rules_text)


if __name__ == "__main__":
    unittest.main()
