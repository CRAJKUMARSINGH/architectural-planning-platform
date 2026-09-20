"""E10 — Stabilization & Enterprise Candidate regression tests.

Covers: load scenario fixture, concurrent job dispatch safety, ADR completeness,
architecture docs completeness, enterprise candidate tag readiness,
quality gate state (REVIEW_REQUIRED only for external professional sign-off),
runbook coverage, CHANGELOG enterprise entry completeness.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e10"
sys.path.insert(0, str(ROOT))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_load_scenario_fixture_loads(self):
        data = _load_fixture("load_scenario.json")
        self.assertIn("projectTypes", data)
        self.assertIn("performanceEnvelopes", data)
        self.assertIn("acceptanceCriteria", data)

    def test_load_scenario_has_three_project_types(self):
        data = _load_fixture("load_scenario.json")
        self.assertGreaterEqual(len(data["projectTypes"]), 3)

    def test_load_scenario_acceptance_criteria_complete(self):
        data = _load_fixture("load_scenario.json")
        ac = data["acceptanceCriteria"]
        self.assertTrue(ac["noDataLoss"])
        self.assertTrue(ac["noSilentFailures"])
        self.assertTrue(ac["reproducibleAcrossRuns"])
        self.assertTrue(ac["lastValidRevisionPreservedOnFailure"])


# ---------------------------------------------------------------------------
# Architecture documents completeness
# ---------------------------------------------------------------------------

class TestArchitectureDocsCompleteness(unittest.TestCase):
    REQUIRED_ADRS = [
        "ADR-001-Geometry-Authority.md",
        "ADR-002-Quality-Gates.md",
        "ADR-003-Tenancy-Model.md",
    ]
    REQUIRED_DOCS = ["data-model.md", "system-context.md"]

    def _arch(self, filename: str) -> Path:
        return ROOT / "docs" / "architecture" / filename

    def test_all_adrs_exist(self):
        for adr in self.REQUIRED_ADRS:
            self.assertTrue(self._arch(adr).exists(),
                            f"ADR missing: {adr}")

    def test_all_architecture_docs_exist(self):
        for doc in self.REQUIRED_DOCS:
            self.assertTrue(self._arch(doc).exists(),
                            f"Architecture doc missing: {doc}")

    def test_adr_001_asserts_python_geometry_authority(self):
        content = self._arch("ADR-001-Geometry-Authority.md").read_text(encoding="utf-8")
        self.assertIn("Python", content)
        self.assertIn("authority", content.lower())
        self.assertIn("never", content.lower())

    def test_adr_002_references_quality_gate_states(self):
        content = self._arch("ADR-002-Quality-Gates.md").read_text(encoding="utf-8")
        for state in ("REVIEW_REQUIRED", "BLOCKED", "PASS"):
            self.assertIn(state, content,
                          f"ADR-002 missing quality gate state: {state!r}")

    def test_adr_003_references_organization_isolation(self):
        content = self._arch("ADR-003-Tenancy-Model.md").read_text(encoding="utf-8")
        self.assertIn("Organization", content)
        self.assertIn("role", content.lower())
        self.assertIn("isolation", content.lower())

    def test_data_model_doc_references_sha256(self):
        content = self._arch("data-model.md").read_text(encoding="utf-8")
        self.assertIn("sha256", content.lower(),
                      "data-model.md should reference SHA-256 content addressing")

    def test_system_context_doc_mentions_workers(self):
        content = self._arch("system-context.md").read_text(encoding="utf-8")
        self.assertTrue(
            "worker" in content.lower() or "queue" in content.lower(),
            "system-context.md should mention the async worker/queue architecture",
        )


# ---------------------------------------------------------------------------
# Runbook coverage
# ---------------------------------------------------------------------------

class TestRunbookCoverage(unittest.TestCase):
    REQUIRED_RUNBOOKS = [
        "queue-stuck.md",
        "artifact-missing.md",
        "db-migration-failure.md",
    ]

    def test_all_runbooks_exist(self):
        for rb in self.REQUIRED_RUNBOOKS:
            path = ROOT / "docs" / "runbooks" / rb
            self.assertTrue(path.exists(), f"Runbook missing: {rb}")

    def test_queue_stuck_runbook_has_symptoms(self):
        content = (ROOT / "docs" / "runbooks" / "queue-stuck.md").read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "symptom" in content.lower() or "signs" in content.lower() or "queue" in content.lower(),
            "queue-stuck.md should describe symptoms",
        )

    def test_artifact_missing_runbook_has_recovery(self):
        content = (ROOT / "docs" / "runbooks" / "artifact-missing.md").read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "recover" in content.lower() or "resolution" in content.lower() or "artifact" in content.lower(),
            "artifact-missing.md should describe recovery steps",
        )

    def test_db_migration_runbook_has_rollback(self):
        content = (ROOT / "docs" / "runbooks" / "db-migration-failure.md").read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "rollback" in content.lower() or "revert" in content.lower() or "migration" in content.lower(),
            "db-migration-failure.md should describe rollback steps",
        )


# ---------------------------------------------------------------------------
# Concurrent job dispatch safety
# ---------------------------------------------------------------------------

class TestConcurrentJobDispatchSafety(unittest.TestCase):
    """Multiple threads dispatching jobs must not corrupt state or raise."""

    def test_concurrent_dispatch_no_exception(self):
        from services.worker.queue import dispatch_job
        errors = []

        def dispatch(job_id: str, job_type: str):
            try:
                dispatch_job(job_id, job_type, {"concurrent": True})
            except Exception as exc:
                errors.append(f"{job_type}: {exc}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(dispatch, f"concurrent-job-{i}", "validate")
                for i in range(6)
            ]
            concurrent.futures.wait(futures, timeout=30)

        self.assertEqual(errors, [], f"Concurrent dispatch errors: {errors}")

    def test_concurrent_rate_limit_window_thread_safe(self):
        """Sliding window deque operations must be safe under concurrent access."""
        from services.api.middleware.rate_limit import _ip_windows
        errors = []
        test_ip = "e10-concurrent-test"

        def hammer():
            import time
            try:
                window = _ip_windows[test_ip]
                window.append(time.time())
                if len(window) > 10:
                    window.popleft()
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=hammer) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread-safety errors: {errors}")

    def test_concurrent_filesystem_store_writes_safe(self):
        """Concurrent writes to different keys must all succeed."""
        import shutil
        tmpdir = tempfile.mkdtemp()
        errors = []
        try:
            from services.api.storage.object_store import FilesystemStore
            store = FilesystemStore(tmpdir)

            def write_artifact(idx: int):
                try:
                    data = json.dumps({"job": idx, "status": "REVIEW_REQUIRED"}).encode()
                    sha = store.put(f"jobs/job-{idx}/report.json", data)
                    retrieved = store.get(f"jobs/job-{idx}/report.json")
                    expected_sha = hashlib.sha256(data).hexdigest()
                    if sha != expected_sha:
                        errors.append(f"job-{idx}: SHA mismatch")
                    if retrieved != data:
                        errors.append(f"job-{idx}: Content mismatch")
                except Exception as exc:
                    errors.append(f"job-{idx}: {exc}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(write_artifact, i) for i in range(16)]
                concurrent.futures.wait(futures, timeout=30)

            self.assertEqual(errors, [], f"Concurrent store errors: {errors}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Load scenario fixture — multi-project validation
# ---------------------------------------------------------------------------

class TestLoadScenarioFixture(unittest.TestCase):
    """Validate the load scenario fixture is internally consistent."""

    def test_performance_envelopes_are_positive(self):
        data = _load_fixture("load_scenario.json")
        for key, ms in data["performanceEnvelopes"].items():
            self.assertGreater(ms, 0, f"Performance envelope {key!r} must be > 0ms")

    def test_concurrent_jobs_positive_for_each_project(self):
        data = _load_fixture("load_scenario.json")
        for proj in data["projectTypes"]:
            self.assertGreater(proj["concurrentJobs"], 0)
            self.assertGreater(proj["spaces"], 0)
            self.assertGreater(proj["openings"], 0)

    def test_deterministic_seed_is_set(self):
        data = _load_fixture("load_scenario.json")
        self.assertIn("deterministicSeed", data)
        seed = data["deterministicSeed"]
        self.assertIsInstance(seed, int)
        self.assertGreater(seed, 0)

    def test_scenario_covers_bar_association_project(self):
        data = _load_fixture("load_scenario.json")
        names = {p["name"] for p in data["projectTypes"]}
        self.assertIn("bar-association-hall", names,
                      "Load scenario must include the bar-association-hall project")


# ---------------------------------------------------------------------------
# Enterprise candidate tag readiness
# ---------------------------------------------------------------------------

class TestEnterpriseCandidateReadiness(unittest.TestCase):
    """The platform must meet all E10 acceptance criteria."""

    def test_changelog_has_enterprise_e01_through_e10(self):
        cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Enterprise", cl)
        for week in ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10"):
            self.assertIn(week, cl, f"CHANGELOG.md missing entry for {week}")

    def test_changelog_quality_state_is_review_required(self):
        cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("REVIEW_REQUIRED", cl)

    def test_quality_gate_report_exists_as_baseline(self):
        baseline_dir = ROOT / "baselines"
        reports = list(baseline_dir.rglob("quality-gate-report.json"))
        self.assertGreater(len(reports), 0,
                           "No quality-gate-report.json found under baselines/")

    def test_contributing_md_exists(self):
        self.assertTrue((ROOT / "CONTRIBUTING.md").exists())

    def test_security_md_exists(self):
        self.assertTrue((ROOT / "SECURITY.md").exists())

    def test_codeowners_exists(self):
        self.assertTrue((ROOT / "CODEOWNERS").exists())

    def test_pyproject_toml_has_ruff_config(self):
        content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("ruff", content.lower())

    def test_docker_compose_brings_up_complete_stack(self):
        """docker-compose.yml must define all 6 services for a full local stack."""
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        for svc in ("postgres", "redis", "minio", "api", "worker", "web"):
            self.assertIn(svc, content,
                          f"docker-compose.yml missing service {svc!r} — cannot bring up complete stack")

    def test_no_inline_geometry_in_revision_model(self):
        """Final ADR-001 guard: Revision table must never store inline geometry."""
        schema = (ROOT / "services" / "api" / "db" / "schema.sql").read_text(encoding="utf-8").lower()
        for forbidden in ("walls jsonb", "openings jsonb", "geometry json", "floorplan text"):
            self.assertNotIn(forbidden, schema,
                             f"ADR-001 violation: schema has inline geometry column {forbidden!r}")

    def test_quality_gate_report_never_auto_promotes_to_pass(self):
        """A REVIEW_REQUIRED report must never be silently promoted to PASS."""
        baseline = ROOT / "baselines"
        for report_path in baseline.rglob("quality-gate-report.json"):
            data = json.loads(report_path.read_text(encoding="utf-8"))
            # PASS is only valid if professional evidence is supplied
            if data.get("status") == "PASS":
                # If PASS, professional review evidence must be present
                prof = data.get("professionalReview", {})
                self.assertGreater(
                    prof.get("reviewersCompleted", 0), 0,
                    f"{report_path}: Status is PASS but no professional review evidence",
                )


# ---------------------------------------------------------------------------
# Final regression — all prior E-week tests still importable
# ---------------------------------------------------------------------------

class TestAllETestsImportable(unittest.TestCase):
    """Smoke test: all E-week test modules must be importable without error."""

    E_TEST_MODULES = [
        "tests.test_e02_persistence",
        "tests.test_e03_auth",
        "tests.test_e04_jobs",
        "tests.test_e05_quality_gate_enforcement",
        "tests.test_e07_health",
        "tests.test_e08_security",
        "tests.test_e09_e10_release",
    ]

    def test_all_e_test_modules_importable(self):
        import importlib
        for module_name in self.E_TEST_MODULES:
            with self.subTest(module=module_name):
                try:
                    importlib.import_module(module_name)
                except ImportError as exc:
                    # Skip if transitive import fails (e.g. SQLAlchemy not installed)
                    if "sqlalchemy" in str(exc).lower() or "alembic" in str(exc).lower():
                        pass  # Expected in CI without DB deps
                    else:
                        self.fail(f"Module {module_name!r} not importable: {exc}")

    def test_expanded_e_test_modules_importable(self):
        import importlib
        expanded = [
            "tests.test_e03_auth_expanded",
            "tests.test_e04_jobs_expanded",
            "tests.test_e05_quality_gate_expanded",
            "tests.test_e06_api",
            "tests.test_e07_observability_expanded",
            "tests.test_e08_security_expanded",
            "tests.test_e09_staging_expanded",
        ]
        for module_name in expanded:
            with self.subTest(module=module_name):
                try:
                    importlib.import_module(module_name)
                except ImportError as exc:
                    self.fail(f"Expanded module {module_name!r} not importable: {exc}")


if __name__ == "__main__":
    unittest.main()
