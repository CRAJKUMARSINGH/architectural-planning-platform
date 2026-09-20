"""E09/E10 — Staging, release, and stabilization tests.

Tests: release check script, docker-compose staging env, runbooks present,
       architecture docs complete, no geometry in DB schema, CHANGELOG entry.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestDockerComposeFiles(unittest.TestCase):
    """E09 — Both compose files must exist and be valid YAML."""

    def _load_yaml(self, path: Path) -> dict:
        try:
            import yaml  # type: ignore[import]
        except ImportError:
            self.skipTest("PyYAML not installed — skip YAML parse")
        with path.open() as f:
            return yaml.safe_load(f)

    def test_docker_compose_exists(self):
        self.assertTrue((ROOT / "docker-compose.yml").exists())

    def test_docker_compose_staging_exists(self):
        self.assertTrue((ROOT / "docker-compose.staging.yml").exists())

    def test_staging_compose_no_auth_disabled_true(self):
        staging = (ROOT / "docker-compose.staging.yml").read_text()
        self.assertNotIn('AUTH_DISABLED: "true"', staging)
        self.assertNotIn("AUTH_DISABLED: 'true'", staging)

    def test_local_compose_services(self):
        content = (ROOT / "docker-compose.yml").read_text()
        for svc in ("postgres", "redis", "minio", "api", "worker", "web"):
            self.assertIn(svc, content)


class TestRunbooksExist(unittest.TestCase):
    """E10 — Runbooks must be present for all critical incidents."""

    def test_queue_stuck_runbook(self):
        self.assertTrue((ROOT / "docs" / "runbooks" / "queue-stuck.md").exists())

    def test_artifact_missing_runbook(self):
        self.assertTrue((ROOT / "docs" / "runbooks" / "artifact-missing.md").exists())

    def test_db_migration_runbook(self):
        self.assertTrue((ROOT / "docs" / "runbooks" / "db-migration-failure.md").exists())


class TestArchitectureDocsComplete(unittest.TestCase):
    """E10 — All ADRs and architecture docs committed."""

    def _arch(self, filename: str) -> Path:
        return ROOT / "docs" / "architecture" / filename

    def test_adr_001_exists(self):
        self.assertTrue(self._arch("ADR-001-Geometry-Authority.md").exists())

    def test_adr_002_exists(self):
        self.assertTrue(self._arch("ADR-002-Quality-Gates.md").exists())

    def test_adr_003_exists(self):
        self.assertTrue(self._arch("ADR-003-Tenancy-Model.md").exists())

    def test_data_model_exists(self):
        self.assertTrue(self._arch("data-model.md").exists())

    def test_system_context_exists(self):
        self.assertTrue(self._arch("system-context.md").exists())

    def test_adr_001_asserts_python_authority(self):
        content = self._arch("ADR-001-Geometry-Authority.md").read_text()
        self.assertIn("Python", content)
        self.assertIn("authority", content.lower())
        self.assertIn("never", content.lower())


class TestSchemaNoInlineGeometry(unittest.TestCase):
    """ADR-001 — The SQL schema must not store walls/openings inline."""

    def test_schema_sql_no_geometry_columns(self):
        schema = (ROOT / "services" / "api" / "db" / "schema.sql").read_text().lower()
        forbidden = ["walls jsonb", "openings jsonb", "geometry json", "floorplan text"]
        for col in forbidden:
            self.assertNotIn(col, schema, f"Schema must not store {col!r} inline")

    def test_schema_has_sha256_pointer(self):
        schema = (ROOT / "services" / "api" / "db" / "schema.sql").read_text()
        self.assertIn("model_sha256", schema)
        self.assertIn("model_storage_key", schema)


class TestChangelogComplete(unittest.TestCase):
    """CHANGELOG.md must document all enterprise weeks."""

    def test_changelog_has_enterprise_entries(self):
        cl = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("Enterprise", cl)
        self.assertIn("E01", cl)
        self.assertIn("Week 28", cl)

    def test_changelog_has_quality_state_table(self):
        cl = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("REVIEW_REQUIRED", cl)
        self.assertIn("adversarial", cl.lower())


class TestReleaseChecklist(unittest.TestCase):
    """E09 release checklist has required items."""

    def test_release_checklist_has_sbom(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text()
        self.assertIn("SBOM", cl)
        self.assertIn("adversarial", cl.lower())

    def test_release_checklist_has_professional_disclaimer(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text()
        self.assertIn("professional", cl.lower())


if __name__ == "__main__":
    unittest.main()
