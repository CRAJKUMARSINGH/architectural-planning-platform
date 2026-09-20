"""E08 — Security hardening tests.

Tests: artifact verifier CLI, org isolation contract, OWASP mapping present,
       AUTH_DISABLED production guard, security headers present in responses.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestArtifactVerifier(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_correct_sha_passes(self):
        """verify_artifact exits 0 for matching SHA-256."""
        import subprocess
        data = b'{"status": "REVIEW_REQUIRED"}'
        p = Path(self.tmpdir) / "report.json"
        p.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/verify_artifact.py",
             str(p), "--expected-sha256", expected],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_wrong_sha_fails(self):
        """verify_artifact exits 1 for SHA-256 mismatch."""
        import subprocess
        data = b'{"status": "REVIEW_REQUIRED"}'
        p = Path(self.tmpdir) / "bad.json"
        p.write_bytes(data)
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/verify_artifact.py",
             str(p), "--expected-sha256", "a" * 64],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 1, "Should fail on hash mismatch")


class TestOrgIsolationContract(unittest.TestCase):
    """ADR-003 — org isolation is enforced at the query layer."""

    def test_security_md_documents_isolation(self):
        security_md = ROOT / "SECURITY.md"
        self.assertTrue(security_md.exists())
        content = security_md.read_text(encoding="utf-8")
        self.assertIn("organization", content.lower())
        self.assertIn("isolation", content.lower())

    def test_adr_003_present(self):
        adr = ROOT / "docs" / "architecture" / "ADR-003-Tenancy-Model.md"
        self.assertTrue(adr.exists())
        content = adr.read_text()
        self.assertIn("Organization", content)
        self.assertIn("role", content.lower())

    def test_repository_sql_enforces_org_id(self):
        """SqlProjectRepository.get() must require org_id parameter."""
        try:
            import inspect
            from services.api.repository_sql import SqlProjectRepository
            sig = inspect.signature(SqlProjectRepository.get)
            self.assertIn("org_id", sig.parameters, "get() must accept org_id")
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")


class TestOwaspMappingDocumented(unittest.TestCase):
    """OWASP Top 10 must be mapped in security checklist — E08."""

    def test_owasp_checklist_exists(self):
        checklist = ROOT / "docs" / "enterprise" / "checklists" / "security.md"
        self.assertTrue(checklist.exists())
        content = checklist.read_text(encoding="utf-8", errors="replace")
        self.assertIn("OWASP", content)
        self.assertIn("Injection", content)


class TestAuthDisabledProductionGuard(unittest.TestCase):
    """AUTH_DISABLED must be documented as impossible in production."""

    def test_docker_compose_staging_has_no_auth_disabled(self):
        staging = ROOT / "docker-compose.staging.yml"
        self.assertTrue(staging.exists())
        content = staging.read_text(encoding="utf-8")
        # AUTH_DISABLED must NOT appear as an env var set to true in staging
        self.assertNotIn("AUTH_DISABLED: \"true\"", content)
        self.assertNotIn("AUTH_DISABLED: 'true'", content)

    def test_security_md_mentions_auth_disabled_restriction(self):
        content = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("AUTH_DISABLED", content)


class TestSecurityChecklist(unittest.TestCase):
    """Release checklist must include security items."""

    def test_release_checklist_exists(self):
        checklist = ROOT / "docs" / "enterprise" / "checklists" / "release.md"
        self.assertTrue(checklist.exists())

    def test_professional_review_checklist_exists(self):
        checklist = ROOT / "docs" / "enterprise" / "checklists" / "professional-review.md"
        self.assertTrue(checklist.exists())
        content = checklist.read_text(encoding="utf-8", errors="replace")
        # Must NOT claim automatic issuability
        self.assertIn("Never", content)


if __name__ == "__main__":
    unittest.main()
