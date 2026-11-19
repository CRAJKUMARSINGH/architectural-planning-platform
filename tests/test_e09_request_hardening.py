"""E09 — Request hardening tests: security headers, body-size limit, rate limit."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from services.api.main import app  # noqa: E402
from services.api.middleware import rate_limit as rl  # noqa: E402


class TestSecurityHeaders(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_security_headers_present_on_health(self):
        resp = self.client.get("/health")
        for header in (
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
            "Content-Security-Policy",
        ):
            self.assertIn(header, resp.headers, f"missing security header: {header}")

    def test_csp_is_strict(self):
        resp = self.client.get("/health")
        self.assertIn("default-src 'none'", resp.headers["Content-Security-Policy"])

    def test_server_header_not_leaked(self):
        resp = self.client.get("/health")
        self.assertNotIn("server", {k.lower() for k in resp.headers})


class TestBodySizeLimit(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_oversized_body_rejected(self):
        from services.api.middleware import body_limit

        with mock.patch.object(body_limit, "MAX_BODY_BYTES", 64):
            resp = self.client.post("/api/v1/projects/", json={"payload": "x" * 500})
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["error"], "payload_too_large")

    def test_oversized_response_keeps_security_headers(self):
        from services.api.middleware import body_limit

        with mock.patch.object(body_limit, "MAX_BODY_BYTES", 64):
            resp = self.client.post("/api/v1/projects/", json={"payload": "x" * 500})
        self.assertIn("X-Content-Type-Options", resp.headers)

    def test_normal_body_passes_through(self):
        resp = self.client.post("/api/v1/projects/", json={"name": "small"})
        self.assertNotEqual(resp.status_code, 413)


class TestRateLimit(unittest.TestCase):
    def setUp(self) -> None:
        rl._ip_windows.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        rl._ip_windows.clear()

    def test_rate_limit_disabled_in_development(self):
        with mock.patch.object(rl, "ENV", "development"):
            codes = [self.client.get("/health").status_code for _ in range(5)]
        self.assertNotIn(429, codes)

    def test_rate_limit_enforced_when_enabled(self):
        with mock.patch.object(rl, "ENV", "production"), \
                mock.patch.object(rl, "RATE_LIMIT", 3):
            codes = [self.client.get("/api/v1/projects/00000000-0000-0000-0000-000000000001").status_code
                     for _ in range(5)]
        self.assertIn(429, codes)
        self.assertEqual(codes[:3], [c for c in codes[:3] if c != 429])

    def test_429_response_has_retry_after_and_security_headers(self):
        with mock.patch.object(rl, "ENV", "production"), \
                mock.patch.object(rl, "RATE_LIMIT", 1):
            self.client.get("/api/v1/projects/00000000-0000-0000-0000-000000000001")
            resp = self.client.get("/api/v1/projects/00000000-0000-0000-0000-000000000001")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Retry-After", resp.headers)
        self.assertIn("X-Content-Type-Options", resp.headers)


if __name__ == "__main__":
    unittest.main()
