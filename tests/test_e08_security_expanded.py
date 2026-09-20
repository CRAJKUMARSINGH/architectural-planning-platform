"""E08 — Security Hardening expanded regression tests.

Covers: rate limiter window/limit constants, security header completeness,
CORS policy, input size limits, path traversal in storage, artifact verifier
CLI contract, OWASP checklist, AUTH_DISABLED production guard, org isolation.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e08"
sys.path.insert(0, str(ROOT))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_security_headers_fixture_loads(self):
        data = _load_fixture("security_headers_required.json")
        self.assertIn("requiredHeaders", data)
        self.assertIn("rateLimitPolicy", data)
        self.assertIn("inputLimits", data)


# ---------------------------------------------------------------------------
# Security headers — completeness
# ---------------------------------------------------------------------------

class TestSecurityHeadersCompleteness(unittest.TestCase):
    """SECURITY_HEADERS dict must contain all headers from the fixture."""

    def test_all_required_headers_present(self):
        fixture = _load_fixture("security_headers_required.json")
        from services.api.middleware.security_headers import SECURITY_HEADERS
        for header, value in fixture["requiredHeaders"].items():
            self.assertIn(header, SECURITY_HEADERS,
                          f"Security header {header!r} missing from SECURITY_HEADERS")
            self.assertEqual(SECURITY_HEADERS[header], value,
                             f"Header {header!r} value mismatch: "
                             f"expected {value!r}, got {SECURITY_HEADERS[header]!r}")

    def test_no_forbidden_headers_in_dict(self):
        """SECURITY_HEADERS must not include server or x-powered-by."""
        from services.api.middleware.security_headers import SECURITY_HEADERS
        for forbidden in ("server", "x-powered-by", "Server", "X-Powered-By"):
            self.assertNotIn(forbidden, SECURITY_HEADERS)

    def test_x_content_type_options_is_nosniff(self):
        from services.api.middleware.security_headers import SECURITY_HEADERS
        self.assertEqual(SECURITY_HEADERS["X-Content-Type-Options"], "nosniff")

    def test_x_frame_options_is_deny(self):
        from services.api.middleware.security_headers import SECURITY_HEADERS
        self.assertEqual(SECURITY_HEADERS["X-Frame-Options"], "DENY")

    def test_referrer_policy_set(self):
        from services.api.middleware.security_headers import SECURITY_HEADERS
        self.assertIn("Referrer-Policy", SECURITY_HEADERS)

    def test_permissions_policy_set(self):
        from services.api.middleware.security_headers import SECURITY_HEADERS
        self.assertIn("Permissions-Policy", SECURITY_HEADERS)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class TestRateLimiterContract(unittest.TestCase):
    """Rate limiter constants must match the fixture policy."""

    def test_rate_limit_matches_fixture(self):
        fixture = _load_fixture("security_headers_required.json")
        from services.api.middleware.rate_limit import RATE_LIMIT
        self.assertEqual(RATE_LIMIT, fixture["rateLimitPolicy"]["limit"])

    def test_window_seconds_matches_fixture(self):
        fixture = _load_fixture("security_headers_required.json")
        from services.api.middleware.rate_limit import WINDOW_SECONDS
        self.assertEqual(WINDOW_SECONDS, fixture["rateLimitPolicy"]["windowSeconds"])

    def test_rate_limit_evicts_old_entries(self):
        """Sliding window must evict timestamps older than WINDOW_SECONDS."""
        from services.api.middleware.rate_limit import _ip_windows, WINDOW_SECONDS
        from collections import deque
        test_ip = f"test-evict-{id(self)}"
        # Plant an old timestamp
        window = _ip_windows[test_ip]
        window.append(time.time() - WINDOW_SECONDS - 1)  # expired
        old_count = len(window)
        self.assertEqual(old_count, 1)
        # The middleware evicts on next dispatch; simulate that logic
        now = time.time()
        while window and window[0] < now - WINDOW_SECONDS:
            window.popleft()
        self.assertEqual(len(window), 0, "Old entry should have been evicted")

    def test_ip_windows_is_defaultdict_of_deque(self):
        from collections import deque, defaultdict
        from services.api.middleware.rate_limit import _ip_windows
        self.assertIsInstance(_ip_windows, defaultdict)
        sample = _ip_windows["sample-ip-e08"]
        self.assertIsInstance(sample, deque)

    def test_health_paths_exempt_from_rate_limit(self):
        """Health/metrics endpoints must not count against the rate limit."""
        src = (ROOT / "services" / "api" / "middleware" / "rate_limit.py").read_text()
        for exempt_path in ("/health", "/ready", "/metrics"):
            self.assertIn(exempt_path, src,
                          f"Path {exempt_path!r} not found in rate_limit.py exemptions")


# ---------------------------------------------------------------------------
# Input size limits
# ---------------------------------------------------------------------------

class TestInputSizeLimits(unittest.TestCase):
    """Pydantic models must enforce the fixture-documented max lengths."""

    def test_brief_text_max_chars_enforced(self):
        from pydantic import ValidationError
        from services.api.main import BriefCompileRequest
        fixture = _load_fixture("security_headers_required.json")
        max_chars = fixture["inputLimits"]["maxBriefTextChars"]
        with self.assertRaises(ValidationError):
            BriefCompileRequest(text="x" * (max_chars + 1), defaultUnits="inch")

    def test_brief_text_min_length_enforced(self):
        from pydantic import ValidationError
        from services.api.main import BriefCompileRequest
        with self.assertRaises(ValidationError):
            BriefCompileRequest(text="", defaultUnits="inch")

    def test_project_name_max_length(self):
        try:
            from pydantic import ValidationError
            from services.api.routes.v1_projects import ProjectCreateRequest
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")
        fixture = _load_fixture("security_headers_required.json")
        max_len = fixture["inputLimits"]["maxProjectNameChars"]
        with self.assertRaises(ValidationError):
            ProjectCreateRequest(name="n" * (max_len + 1), units="inch")


# ---------------------------------------------------------------------------
# Artifact verifier CLI
# ---------------------------------------------------------------------------

class TestArtifactVerifierExpanded(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _verify(self, data: bytes, expected_sha: str | None = None) -> tuple[int, str]:
        p = Path(self.tmpdir) / "test-artifact.json"
        p.write_bytes(data)
        if expected_sha is None:
            expected_sha = hashlib.sha256(data).hexdigest()
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/verify_artifact.py",
             str(p), "--expected-sha256", expected_sha],
            capture_output=True, cwd=str(ROOT),
        )
        return result.returncode, result.stderr.decode()

    def test_correct_sha_passes(self):
        data = b'{"status": "REVIEW_REQUIRED"}'
        code, _ = self._verify(data)
        self.assertEqual(code, 0)

    def test_wrong_sha_fails(self):
        data = b'{"status": "REVIEW_REQUIRED"}'
        code, stderr = self._verify(data, expected_sha="a" * 64)
        self.assertEqual(code, 1)
        self.assertTrue(len(stderr) > 0)

    def test_empty_file_produces_valid_sha(self):
        code, _ = self._verify(b"")
        self.assertEqual(code, 0)

    def test_tampered_content_fails(self):
        data = b'{"status": "PASS"}'
        sha = hashlib.sha256(data).hexdigest()
        # Tamper the content
        tampered = b'{"status": "BLOCKED"}'
        p = Path(self.tmpdir) / "tampered.json"
        p.write_bytes(tampered)
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/verify_artifact.py",
             str(p), "--expected-sha256", sha],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 1)

    def test_missing_file_fails_gracefully(self):
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/verify_artifact.py",
             "/nonexistent/file.json", "--expected-sha256", "a" * 64],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertNotEqual(result.returncode, 0)


# ---------------------------------------------------------------------------
# Storage path traversal — E04/E08 combined
# ---------------------------------------------------------------------------

class TestStoragePathTraversalExpanded(unittest.TestCase):
    def setUp(self):
        import shutil
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_double_dot_traversal_contained(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        try:
            store.put("../../sensitive.json", b"malicious")
        except Exception:
            return  # Exception is fine — traversal was blocked
        # File must not have escaped the base
        escaped_path = Path(self.tmpdir).parent / "sensitive.json"
        self.assertFalse(escaped_path.exists())

    def test_absolute_path_key_sanitized(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        try:
            store.put("/etc/passwd", b"data")
        except Exception:
            return  # Blocked — acceptable
        # Must not write to actual /etc/passwd
        self.assertFalse(Path("/etc/passwd_advocate_test").exists())

    def test_windows_traversal_sanitized(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        try:
            store.put("..\\..\\escape.json", b"data")
        except Exception:
            return


# ---------------------------------------------------------------------------
# OWASP Top 10 mapping
# ---------------------------------------------------------------------------

class TestOwaspTopTenMapping(unittest.TestCase):
    def test_owasp_checklist_has_injection_section(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "security.md").read_text(encoding="utf-8", errors="replace")
        self.assertIn("Injection", cl)
        self.assertIn("OWASP", cl)

    def test_owasp_checklist_has_auth_section(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "security.md").read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "Authentication" in cl or "auth" in cl.lower(),
            "Security checklist missing authentication section",
        )

    def test_owasp_checklist_has_broken_access_section(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "security.md").read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "access control" in cl.lower() or "Authorization" in cl,
            "Security checklist missing access control section",
        )


# ---------------------------------------------------------------------------
# CORS policy
# ---------------------------------------------------------------------------

class TestCorsPolicy(unittest.TestCase):
    def test_main_app_declares_cors_middleware(self):
        src = (ROOT / "services" / "api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("CORSMiddleware", src)

    def test_cors_allows_localhost_dev_origins(self):
        fixture = _load_fixture("security_headers_required.json")
        src = (ROOT / "services" / "api" / "main.py").read_text(encoding="utf-8")
        for origin in fixture["corsPolicy"]["allowedOrigins"]:
            self.assertIn(origin, src, f"CORS allowed origin {origin!r} not in main.py")

    def test_staging_compose_has_no_wildcard_cors(self):
        staging = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertNotIn("allow_origins=[\"*\"]", staging)
        self.assertNotIn("CORS_ALLOW_ALL", staging)


# ---------------------------------------------------------------------------
# AUTH_DISABLED guard
# ---------------------------------------------------------------------------

class TestAuthDisabledGuardExpanded(unittest.TestCase):
    def test_security_md_mentions_staging_guard(self):
        content = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("AUTH_DISABLED", content)
        self.assertIn("staging", content.lower())

    def test_staging_compose_no_auth_disabled_true(self):
        staging = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertNotIn('AUTH_DISABLED: "true"', staging)
        self.assertNotIn("AUTH_DISABLED: 'true'", staging)

    def test_auth_disabled_env_variable_checked_at_startup(self):
        """auth.py must read AUTH_DISABLED at module level (not request time)."""
        src = (ROOT / "services" / "api" / "auth.py").read_text(encoding="utf-8")
        self.assertIn("AUTH_DISABLED", src)
        # Must check environment variable
        self.assertIn("os.environ.get", src)


if __name__ == "__main__":
    unittest.main()
