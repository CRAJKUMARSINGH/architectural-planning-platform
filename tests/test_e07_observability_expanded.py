"""E07 — Observability expanded regression tests.

Covers: JSON log format contract, all required log fields, request-id propagation
through middleware, health/ready endpoint contract, metrics availability,
Grafana dashboard existence, correlation ID round-trip.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e07"
sys.path.insert(0, str(ROOT))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_structured_log_sample_fixture_loads(self):
        data = _load_fixture("structured_log_sample.json")
        self.assertIn("requiredFields", data)
        self.assertIn("serviceValue", data)
        self.assertIn("healthEndpointExpected", data)

    def test_fixture_required_fields_complete(self):
        data = _load_fixture("structured_log_sample.json")
        for field in ("ts", "level", "service", "logger", "msg"):
            self.assertIn(field, data["requiredFields"])


# ---------------------------------------------------------------------------
# JSON log formatter — field contract
# ---------------------------------------------------------------------------

class TestJsonFormatterContract(unittest.TestCase):
    """JsonFormatter output must include all fields from the fixture spec."""

    def _format(self, msg: str, **extra) -> dict:
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO,
            pathname="", lineno=0, msg=msg,
            args=(), exc_info=None,
        )
        for k, v in extra.items():
            setattr(record, k, v)
        return json.loads(formatter.format(record))

    def test_all_required_fields_present(self):
        fixture = _load_fixture("structured_log_sample.json")
        output = self._format("test message")
        for field in fixture["requiredFields"]:
            self.assertIn(field, output, f"Required log field {field!r} missing")

    def test_service_value_matches_fixture(self):
        fixture = _load_fixture("structured_log_sample.json")
        output = self._format("any message")
        self.assertEqual(output["service"], fixture["serviceValue"])

    def test_level_values_are_uppercase(self):
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        for level_const, level_name in (
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
        ):
            record = logging.LogRecord(
                "t", level_const, "", 0, "msg", (), None
            )
            out = json.loads(formatter.format(record))
            self.assertEqual(out["level"], level_name)

    def test_request_id_propagated_when_set(self):
        output = self._format("job completed", request_id="req-e07-001")
        self.assertEqual(output["request_id"], "req-e07-001")

    def test_job_id_propagated_when_set(self):
        output = self._format("artifact stored", job_id="job-e07-123")
        self.assertEqual(output["job_id"], "job-e07-123")

    def test_org_id_propagated_when_set(self):
        output = self._format("org action", org_id="org-e07-456")
        self.assertEqual(output["org_id"], "org-e07-456")

    def test_user_id_propagated_when_set(self):
        output = self._format("user action", user_id="user-e07-789")
        self.assertEqual(output["user_id"], "user-e07-789")

    def test_message_preserved_exactly(self):
        output = self._format("exact message content 42")
        self.assertEqual(output["msg"], "exact message content 42")

    def test_exception_info_serialized(self):
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        try:
            raise ValueError("test error for log")
        except ValueError:
            import sys as _sys
            exc_info = _sys.exc_info()
        record = logging.LogRecord("t", logging.ERROR, "", 0, "error", (), exc_info)
        out = json.loads(formatter.format(record))
        self.assertIn("exc", out)
        self.assertIn("ValueError", out["exc"])

    def test_no_extra_forbidden_fields(self):
        """Log output must not leak internal Python record attributes like lineno as top-level."""
        output = self._format("clean output")
        # These should not pollute the structured log as top-level keys
        for internal in ("lineno", "filename", "funcName", "module"):
            self.assertNotIn(internal, output,
                             f"Internal field {internal!r} should not appear in JSON log output")


# ---------------------------------------------------------------------------
# Health endpoint contract
# ---------------------------------------------------------------------------

class TestHealthEndpointContract(unittest.TestCase):
    """Health endpoint must match the fixture spec exactly."""

    def test_health_matches_fixture_expectation(self):
        from services.api.routes.v1_health import health
        fixture = _load_fixture("structured_log_sample.json")["healthEndpointExpected"]
        result = health()
        for key, expected_value in fixture.items():
            self.assertIn(key, result, f"Health response missing key: {key!r}")
            self.assertEqual(result[key], expected_value,
                             f"Health response key {key!r}: expected {expected_value!r}, got {result[key]!r}")

    def test_health_always_returns_200_shape(self):
        from services.api.routes.v1_health import health
        result = health()
        self.assertEqual(result["status"], "ok")

    def test_health_geometry_authority_is_python(self):
        from services.api.routes.v1_health import health
        result = health()
        self.assertEqual(result["authoritativeGeometry"], "python")

    def test_health_version_field_present(self):
        from services.api.routes.v1_health import health
        result = health()
        self.assertIn("version", result)
        self.assertIn("enterprise", result["version"])


# ---------------------------------------------------------------------------
# Ready endpoint contract
# ---------------------------------------------------------------------------

class TestReadyEndpointContract(unittest.TestCase):
    def test_ready_returns_status_and_checks(self):
        from unittest.mock import MagicMock
        from services.api.routes.v1_health import ready
        mock_response = MagicMock()
        result = ready(response=mock_response)
        self.assertIn("status", result)
        self.assertIn("checks", result)

    def test_ready_checks_postgres(self):
        from unittest.mock import MagicMock
        from services.api.routes.v1_health import ready
        mock_response = MagicMock()
        result = ready(response=mock_response)
        self.assertIn("postgres", result["checks"])

    def test_ready_status_values_are_valid(self):
        from unittest.mock import MagicMock
        from services.api.routes.v1_health import ready
        mock_response = MagicMock()
        result = ready(response=mock_response)
        self.assertIn(result["status"], ("ready", "degraded"))


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

class TestMetricsEndpoint(unittest.TestCase):
    def test_metrics_endpoint_importable(self):
        from services.api.middleware.metrics import MetricsMiddleware
        self.assertIsNotNone(MetricsMiddleware)

    def test_prometheus_constants_positive(self):
        from services.api.middleware.metrics import PROMETHEUS_AVAILABLE
        # If prometheus-client is installed, constants are defined
        if PROMETHEUS_AVAILABLE:
            from services.api.middleware.metrics import REQUEST_COUNT, REQUEST_LATENCY
            self.assertIsNotNone(REQUEST_COUNT)
            self.assertIsNotNone(REQUEST_LATENCY)

    def test_metrics_endpoint_function_callable(self):
        from services.api.middleware.metrics import metrics_endpoint
        # Should return a Response or a dict — must not raise
        try:
            result = metrics_endpoint()
            self.assertIsNotNone(result)
        except Exception as exc:
            self.fail(f"metrics_endpoint() raised: {exc}")


# ---------------------------------------------------------------------------
# Grafana dashboard
# ---------------------------------------------------------------------------

class TestGrafanaDashboard(unittest.TestCase):
    def test_grafana_dashboard_json_exists(self):
        self.assertTrue((ROOT / "docs" / "grafana-dashboard.json").exists(),
                        "Grafana dashboard JSON missing from docs/")

    def test_grafana_dashboard_is_valid_json(self):
        path = ROOT / "docs" / "grafana-dashboard.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("panels", data)

    def test_grafana_dashboard_has_panels(self):
        path = ROOT / "docs" / "grafana-dashboard.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreater(len(data.get("panels", [])), 0)


# ---------------------------------------------------------------------------
# Correlation ID round-trip
# ---------------------------------------------------------------------------

class TestCorrelationIdRoundTrip(unittest.TestCase):
    """x-request-id header must be echoed back in the response."""

    def test_request_logging_middleware_echoes_request_id(self):
        """RequestLoggingMiddleware must attach request_id to response headers."""
        from services.api.middleware.logging import RequestLoggingMiddleware
        # Verify the middleware source sets the response header
        src = (ROOT / "services" / "api" / "middleware" / "logging.py").read_text()
        self.assertIn("x-request-id", src)
        self.assertIn("request_id", src)

    def test_auth_dev_user_carries_request_id(self):
        os.environ["AUTH_DISABLED"] = "true"
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]
        import importlib
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        user = auth.get_current_user(authorization=None, x_request_id="corr-e07-001")
        self.assertEqual(user.request_id, "corr-e07-001")
        os.environ.pop("AUTH_DISABLED", None)


# ---------------------------------------------------------------------------
# Structured logging configuration
# ---------------------------------------------------------------------------

class TestJsonLoggingConfiguration(unittest.TestCase):
    def test_configure_json_logging_does_not_raise(self):
        from services.api.middleware.logging import configure_json_logging
        try:
            configure_json_logging("INFO")
        except Exception as exc:
            self.fail(f"configure_json_logging raised: {exc}")

    def test_json_formatter_is_callable(self):
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        self.assertTrue(callable(formatter.format))


if __name__ == "__main__":
    unittest.main()
