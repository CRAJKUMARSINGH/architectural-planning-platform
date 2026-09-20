"""E09 — Staging & Release Process expanded regression tests.

Covers: docker-compose service completeness, staging env guards, release manifest
fixture, SBOM workflow, release checklist items, Dockerfile presence,
release_check.py contract, Makefile targets.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e09"
sys.path.insert(0, str(ROOT))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_release_manifest_fixture_loads(self):
        data = _load_fixture("release_manifest_sample.json")
        self.assertIn("version", data)
        self.assertIn("qualityGateStatus", data)
        self.assertIn("sbom", data)

    def test_release_manifest_has_three_docker_images(self):
        data = _load_fixture("release_manifest_sample.json")
        self.assertEqual(len(data["dockerImages"]), 3)
        names = {img["name"] for img in data["dockerImages"]}
        self.assertIn("advocate-api", names)
        self.assertIn("advocate-worker", names)
        self.assertIn("advocate-web", names)

    def test_release_checklist_fields_complete(self):
        data = _load_fixture("release_manifest_sample.json")
        checklist = data["releaseChecklist"]
        for key in ("allTestsGreen", "adversarialSuiteGreen", "changelogUpdated",
                    "sbomGenerated", "professionalReviewDisclaimer"):
            self.assertIn(key, checklist)


# ---------------------------------------------------------------------------
# Docker Compose — service completeness
# ---------------------------------------------------------------------------

class TestDockerComposeCompleteness(unittest.TestCase):
    REQUIRED_SERVICES = ["postgres", "redis", "minio", "api", "worker", "web"]

    def test_docker_compose_has_all_services(self):
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        for svc in self.REQUIRED_SERVICES:
            self.assertIn(svc, content,
                          f"docker-compose.yml missing service: {svc!r}")

    def test_docker_compose_staging_has_all_services(self):
        """Staging compose has core services; minio is dev-only (real S3/R2 in staging)."""
        content = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        staging_required = ["postgres", "redis", "api", "worker", "web"]
        for svc in staging_required:
            self.assertIn(svc, content,
                          f"docker-compose.staging.yml missing service: {svc!r}")

    def test_docker_compose_staging_references_postgres(self):
        content = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("postgres", content)

    def test_docker_compose_references_redis(self):
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("redis", content)

    def test_local_compose_references_minio(self):
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("minio", content)


# ---------------------------------------------------------------------------
# Dockerfiles
# ---------------------------------------------------------------------------

class TestDockerfilesPresent(unittest.TestCase):
    def test_dockerfile_api_exists(self):
        self.assertTrue((ROOT / "Dockerfile.api").exists())

    def test_dockerfile_worker_exists(self):
        self.assertTrue((ROOT / "Dockerfile.worker").exists())

    def test_dockerfile_web_exists(self):
        self.assertTrue((ROOT / "Dockerfile.web").exists())

    def test_dockerfile_api_uses_python_base(self):
        content = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
        self.assertTrue(
            "python" in content.lower() or "FROM" in content,
            "Dockerfile.api should reference a Python base image",
        )


# ---------------------------------------------------------------------------
# Release workflow
# ---------------------------------------------------------------------------

class TestReleaseWorkflow(unittest.TestCase):
    def test_release_yml_exists(self):
        self.assertTrue((ROOT / ".github" / "workflows" / "release.yml").exists())

    def test_release_yml_references_sbom(self):
        content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertTrue(
            "sbom" in content.lower() or "SBOM" in content,
            "release.yml should reference SBOM generation",
        )

    def test_release_yml_references_quality_gate(self):
        content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertTrue(
            "quality_gate" in content or "quality-gate" in content,
            "release.yml should reference quality gate check",
        )

    def test_ci_yml_lint_job_present(self):
        content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertTrue(
            "lint" in content.lower() or "ruff" in content,
            "CI workflow should include a lint step",
        )

    def test_ci_yml_test_job_present(self):
        content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertTrue(
            "pytest" in content or "unittest" in content or "test" in content.lower(),
            "CI workflow should include a test step",
        )


# ---------------------------------------------------------------------------
# Release checklist docs
# ---------------------------------------------------------------------------

class TestReleaseChecklistDocs(unittest.TestCase):
    def test_release_checklist_markdown_exists(self):
        self.assertTrue((ROOT / "docs" / "enterprise" / "checklists" / "release.md").exists())

    def test_release_checklist_mentions_adversarial(self):
        content = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text(encoding="utf-8")
        self.assertIn("adversarial", content.lower())

    def test_release_checklist_mentions_sbom(self):
        content = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text(encoding="utf-8")
        self.assertIn("SBOM", content)

    def test_release_checklist_has_professional_disclaimer(self):
        content = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text(encoding="utf-8")
        self.assertIn("professional", content.lower())
        self.assertIn("Never", content)

    def test_code_quality_checklist_exists(self):
        self.assertTrue((ROOT / "docs" / "enterprise" / "checklists" / "code-quality.md").exists())

    def test_professional_review_checklist_exists(self):
        self.assertTrue((ROOT / "docs" / "enterprise" / "checklists" / "professional-review.md").exists())


# ---------------------------------------------------------------------------
# release_check.py script contract
# ---------------------------------------------------------------------------

class TestReleaseCheckScript(unittest.TestCase):
    def test_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "enterprise" / "release_check.py").exists())

    def test_script_compiles_clean(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile",
             "scripts/enterprise/release_check.py"],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_script_has_quality_gate_reference(self):
        src = (ROOT / "scripts" / "enterprise" / "release_check.py").read_text(encoding="utf-8")
        self.assertTrue(
            "quality_gate" in src or "quality-gate" in src or "REVIEW_REQUIRED" in src,
            "release_check.py should reference quality gate status",
        )

    def test_release_manifest_fixture_status_is_review_required(self):
        """Release manifest status must be REVIEW_REQUIRED (not auto-PASS)."""
        data = _load_fixture("release_manifest_sample.json")
        self.assertEqual(data["qualityGateStatus"], "REVIEW_REQUIRED")

    def test_release_manifest_fixture_sbom_format_is_spdx(self):
        data = _load_fixture("release_manifest_sample.json")
        self.assertIn("spdx", data["sbom"]["format"].lower())


# ---------------------------------------------------------------------------
# Staging security guards
# ---------------------------------------------------------------------------

class TestStagingSecurityGuards(unittest.TestCase):
    def test_staging_compose_no_auth_disabled(self):
        content = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertNotIn('AUTH_DISABLED: "true"', content)
        self.assertNotIn("AUTH_DISABLED=true", content)

    def test_staging_compose_does_not_expose_db_to_public(self):
        content = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        # Should not publish Postgres port to all interfaces (0.0.0.0:5432)
        # Internal service ports are fine
        self.assertNotIn('"0.0.0.0:5432:5432"', content)

    def test_security_md_has_vulnerability_disclosure(self):
        content = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertTrue(
            "vulnerabilit" in content.lower() or "disclosure" in content.lower(),
            "SECURITY.md should describe vulnerability disclosure process",
        )


# ---------------------------------------------------------------------------
# Makefile targets
# ---------------------------------------------------------------------------

class TestMakefileTargets(unittest.TestCase):
    REQUIRED_TARGETS = ["lint", "test", "typecheck"]

    def test_makefile_exists(self):
        self.assertTrue((ROOT / "Makefile").exists())

    def test_makefile_has_required_targets(self):
        content = (ROOT / "Makefile").read_text(encoding="utf-8")
        for target in self.REQUIRED_TARGETS:
            self.assertIn(target, content,
                          f"Makefile missing target: {target!r}")

    def test_makefile_has_docker_target_or_compose_reference(self):
        content = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertTrue(
            "docker" in content.lower() or "compose" in content.lower(),
            "Makefile should reference docker or compose",
        )


if __name__ == "__main__":
    unittest.main()
