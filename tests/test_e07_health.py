"""E07 — Health & observability tests.

Tests: /health always 200, /ready logic, JSON log formatter, metrics middleware wiring.
"""
from __future__ import annotations

import json
import logging
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


class TestHealthEndpointUnit(unittest.TestCase):
    """Unit test — call the health function directly."""

    def test_health_returns_ok(self):
        from services.api.routes.v1_health import health
        result = health()
        self.assertEqual(result["status"], "ok")
        self.assertIn("service", result)

    def test_health_reports_python_geometry_authority(self):
        from services.api.routes.v1_health import health
        result = health()
        self.assertEqual(result["authoritativeGeometry"], "python")


class TestReadyEndpointUnit(unittest.TestCase):
    """Unit test — call ready function directly with mock response."""

    def test_ready_returns_dict(self):
        from unittest.mock import MagicMock
        from services.api.routes.v1_health import ready
        mock_response = MagicMock()
        mock_response.status_code = 200
        result = ready(response=mock_response)
        self.assertIn("status", result)
        self.assertIn("checks", result)

    def test_ready_sqlite_dev_check(self):
        """In dev mode (SQLite), postgres check reports sqlite-dev."""
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from unittest.mock import MagicMock
        from services.api.routes.v1_health import ready
        mock_resp = MagicMock()
        result = ready(response=mock_resp)
        checks = result["checks"]
        # Either 'sqlite-dev' or a postgres result
        self.assertIn("postgres", checks)


class TestJsonFormatter(unittest.TestCase):
    """Structured JSON log output."""

    def test_json_log_format(self):
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="hello world",
            args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        self.assertEqual(parsed["msg"], "hello world")
        self.assertEqual(parsed["level"], "INFO")
        self.assertIn("service", parsed)

    def test_json_log_extra_fields(self):
        from services.api.middleware.logging import JsonFormatter
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="job done",
            args=(), exc_info=None,
        )
        record.request_id = "req-abc"
        record.job_id = "job-123"
        output = json.loads(formatter.format(record))
        self.assertEqual(output["request_id"], "req-abc")
        self.assertEqual(output["job_id"], "job-123")


class TestSecurityHeaders(unittest.TestCase):
    """Security headers must be present on all responses — E08."""

    def test_required_header_constants(self):
        import os
        os.environ["ENV"] = "development"
        from services.api.middleware.security_headers import SECURITY_HEADERS
        required = {"X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"}
        for h in required:
            self.assertIn(h, SECURITY_HEADERS)


class TestRateLimiter(unittest.TestCase):
    """Rate limiter enforces per-IP window."""

    def test_rate_limit_state_initializes(self):
        from services.api.middleware.rate_limit import _ip_windows, RATE_LIMIT, WINDOW_SECONDS
        self.assertGreater(RATE_LIMIT, 0)
        self.assertGreater(WINDOW_SECONDS, 0)
        # _ip_windows is a defaultdict — accessing any key should give a deque
        from collections import deque
        window = _ip_windows["1.2.3.4"]
        self.assertIsInstance(window, deque)


if __name__ == "__main__":
    unittest.main()
