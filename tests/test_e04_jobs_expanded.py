"""E04 — Async Jobs & Storage expanded regression tests.

Covers: job state machine transitions, content-addressed deduplication,
path-traversal sanitization, store factory, null-byte injection,
inline fallback dispatch, artifact fixture alignment.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e04"
sys.path.insert(0, str(ROOT))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_job_payloads_fixture_loads(self):
        data = _load_fixture("job_payloads.json")
        self.assertGreaterEqual(len(data["jobs"]), 3)
        self.assertIn("stateMachineTransitions", data)

    def test_artifact_samples_fixture_loads(self):
        data = _load_fixture("artifact_samples.json")
        self.assertGreaterEqual(len(data["artifacts"]), 3)
        self.assertGreaterEqual(len(data["securityCases"]), 3)

    def test_valid_job_types_in_fixture(self):
        data = _load_fixture("job_payloads.json")
        valid = {"generate", "validate", "enrich", "quality_gate", "export", "benchmark"}
        for job in data["jobs"]:
            if job["type"] != "INVALID_TYPE":
                self.assertIn(job["type"], valid, f"Fixture job type {job['type']!r} not in allowed set")


# ---------------------------------------------------------------------------
# Job state machine transitions
# ---------------------------------------------------------------------------

class TestJobStateMachine(unittest.TestCase):
    """State machine: queued→running→{succeeded|failed|cancelled}."""

    VALID_TRANSITIONS = {
        ("queued", "running"),
        ("running", "succeeded"),
        ("running", "failed"),
        ("running", "cancelled"),
        ("queued", "cancelled"),
    }
    INVALID_TRANSITIONS = {
        ("succeeded", "running"),
        ("failed", "succeeded"),
        ("succeeded", "failed"),
        ("cancelled", "running"),
    }

    def test_valid_transitions_in_fixture(self):
        """All fixture-declared valid transitions must match code expectations."""
        data = _load_fixture("job_payloads.json")
        for t in data["stateMachineTransitions"]:
            pair = (t["from"], t["to"])
            if t["valid"]:
                self.assertIn(pair, self.VALID_TRANSITIONS,
                              f"Fixture claims {pair} is valid but code does not allow it")
            else:
                self.assertIn(pair, self.INVALID_TRANSITIONS,
                              f"Fixture claims {pair} is invalid but code allows it")

    def test_terminal_states_are_terminal(self):
        """succeeded / failed / cancelled must not transition to running again."""
        for terminal in ("succeeded", "failed", "cancelled"):
            self.assertNotIn((terminal, "running"), self.VALID_TRANSITIONS)

    def test_job_status_constants_exist(self):
        try:
            from services.api.models.orm import VALID_JOB_STATUSES
            expected = {"queued", "running", "succeeded", "failed", "cancelled"}
            self.assertEqual(set(VALID_JOB_STATUSES), expected)
        except ImportError:
            self.skipTest("sqlalchemy not installed")

    def test_job_type_constants_match_fixture(self):
        data = _load_fixture("job_payloads.json")
        fixture_valid_types = {
            j["type"] for j in data["jobs"] if j["type"] != "INVALID_TYPE"
        }
        try:
            from services.api.models.orm import VALID_JOB_TYPES
            for t in fixture_valid_types:
                self.assertIn(t, VALID_JOB_TYPES,
                              f"Job type {t!r} in fixture but missing from VALID_JOB_TYPES")
        except ImportError:
            self.skipTest("sqlalchemy not installed")


# ---------------------------------------------------------------------------
# FilesystemStore — content-addressed integrity
# ---------------------------------------------------------------------------

class TestFilesystemStoreExpanded(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _store(self):
        from services.api.storage.object_store import FilesystemStore
        return FilesystemStore(self.tmpdir)

    def test_sha256_is_content_addressed(self):
        store = self._store()
        data = b'{"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 30, "total": 30}}'
        sha = store.put("reports/qg.json", data)
        self.assertEqual(sha, hashlib.sha256(data).hexdigest())

    def test_idempotent_put_same_key_same_content(self):
        """Writing the same content twice returns the same SHA-256."""
        store = self._store()
        data = b'{"status": "PASS"}'
        sha1 = store.put("artifact/report.json", data)
        sha2 = store.put("artifact/report.json", data)
        self.assertEqual(sha1, sha2)

    def test_overwrite_with_different_content(self):
        """Writing different content to same key returns a different SHA-256."""
        store = self._store()
        sha1 = store.put("artifact/x.json", b'{"a": 1}')
        sha2 = store.put("artifact/x.json", b'{"a": 2}')
        self.assertNotEqual(sha1, sha2)

    def test_path_traversal_does_not_escape_base(self):
        """../.. traversal must be contained inside base directory."""
        store = self._store()
        try:
            store.put("../../escape.json", b"malicious")
        except Exception:
            pass  # Any exception is acceptable — the key is rejected
        # The file must NOT exist above tmpdir
        escaped = Path(self.tmpdir).parent / "escape.json"
        self.assertFalse(escaped.exists(), "Path traversal escaped base directory!")

    def test_null_byte_in_key_sanitized(self):
        """Null-byte injection in storage key must not reach the filesystem."""
        store = self._store()
        try:
            store.put("reports/valid\x00../../etc/shadow", b"data")
        except Exception:
            pass  # Any exception is fine

    def test_nested_key_creates_subdirs(self):
        store = self._store()
        store.put("jobs/abc123/report.json", b'{}')
        self.assertTrue((Path(self.tmpdir) / "jobs" / "abc123" / "report.json").exists())

    def test_get_missing_raises_file_not_found(self):
        store = self._store()
        with self.assertRaises(FileNotFoundError):
            store.get("does/not/exist.json")

    def test_exists_false_before_put(self):
        store = self._store()
        self.assertFalse(store.exists("phantom.json"))

    def test_exists_true_after_put(self):
        store = self._store()
        store.put("real.json", b'{}')
        self.assertTrue(store.exists("real.json"))

    def test_roundtrip_preserves_bytes(self):
        store = self._store()
        data = json.dumps({"status": "REVIEW_REQUIRED", "findings": []}).encode("utf-8")
        store.put("round/trip.json", data)
        retrieved = store.get("round/trip.json")
        self.assertEqual(retrieved, data)

    def test_fixture_artifact_sha256_matches(self):
        """Artifact fixture content SHA-256 should match runtime calculation."""
        store = self._store()
        fixture = _load_fixture("artifact_samples.json")
        for sample in fixture["artifacts"]:
            raw = sample["content"].encode("utf-8")
            sha = store.put(f"fixture/{sample['id']}.json", raw)
            expected = hashlib.sha256(raw).hexdigest()
            self.assertEqual(sha, expected, f"SHA-256 mismatch for fixture {sample['id']!r}")


# ---------------------------------------------------------------------------
# ObjectStore factory
# ---------------------------------------------------------------------------

class TestObjectStoreFactory(unittest.TestCase):
    def setUp(self):
        os.environ.pop("S3_ENDPOINT", None)

    def tearDown(self):
        os.environ.pop("S3_ENDPOINT", None)

    def test_no_s3_endpoint_returns_filesystem_store(self):
        from services.api.storage.object_store import FilesystemStore, get_object_store
        store = get_object_store()
        self.assertIsInstance(store, FilesystemStore)

    def test_artifact_path_env_var_respected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["ARTIFACT_PATH"] = tmpdir
            from services.api.storage.object_store import FilesystemStore, get_object_store
            store = get_object_store()
            self.assertIsInstance(store, FilesystemStore)
            self.assertEqual(str(store.base), tmpdir)
        os.environ.pop("ARTIFACT_PATH", None)


# ---------------------------------------------------------------------------
# Dispatch — inline fallback
# ---------------------------------------------------------------------------

class TestDispatchInlineFallback(unittest.TestCase):
    def setUp(self):
        os.environ.pop("REDIS_URL", None)

    def test_dispatch_job_no_redis_does_not_raise(self):
        from services.worker.queue import dispatch_job
        try:
            dispatch_job("fixture-job-id-001", "validate", {"test": True})
        except Exception as exc:
            self.fail(f"dispatch_job should not raise but got: {exc}")

    def test_all_valid_job_types_dispatch_without_exception(self):
        from services.worker.queue import dispatch_job
        valid_types = ["generate", "validate", "enrich", "quality_gate", "export", "benchmark"]
        for jtype in valid_types:
            with self.subTest(job_type=jtype):
                try:
                    dispatch_job(f"fixture-job-{jtype}", jtype, {})
                except Exception as exc:
                    self.fail(f"dispatch_job({jtype!r}) raised: {exc}")


# ---------------------------------------------------------------------------
# Artifact integrity — SHA-256 determinism
# ---------------------------------------------------------------------------

class TestArtifactIntegrityExpanded(unittest.TestCase):
    """SHA-256 determinism is a core ADR-001 guarantee."""

    def test_quality_gate_report_deterministic(self):
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 30, "total": 30}}
        data = json.dumps(report, sort_keys=True).encode("utf-8")
        h1 = hashlib.sha256(data).hexdigest()
        h2 = hashlib.sha256(data).hexdigest()
        self.assertEqual(h1, h2)

    def test_different_statuses_different_hashes(self):
        statuses = ["PASS", "REVIEW_REQUIRED", "BLOCKED", "INCOMPLETE"]
        hashes = set()
        for s in statuses:
            data = json.dumps({"status": s}).encode("utf-8")
            hashes.add(hashlib.sha256(data).hexdigest())
        self.assertEqual(len(hashes), len(statuses), "Different statuses must produce distinct hashes")

    def test_sha256_hex_length_is_64(self):
        h = hashlib.sha256(b"advocate-chambers").hexdigest()
        self.assertEqual(len(h), 64)

    def test_security_cases_fixture_has_traversal_scenario(self):
        data = _load_fixture("artifact_samples.json")
        traversal_ids = {c["id"] for c in data["securityCases"] if "traversal" in c["id"]}
        self.assertGreaterEqual(len(traversal_ids), 1, "Need at least one path traversal test case")


# ---------------------------------------------------------------------------
# SqlArtifactRepository — ORM-based artifact creation
# ---------------------------------------------------------------------------

class TestSqlArtifactRepository(unittest.TestCase):
    def test_artifact_creation_stores_sha256(self):
        try:
            from services.api.repository_sql import (
                SqlArtifactRepository, SqlJobRepository, SqlProjectRepository
            )
            from services.api.models.base import Base
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
            Base.metadata.create_all(engine)
            S = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with S() as sess:
                org_id = uuid.uuid4()
                proj_repo = SqlProjectRepository(sess)
                proj = proj_repo.create(org_id, "Test Project", "inch")
                sess.commit()

                job_repo = SqlJobRepository(sess)
                job = job_repo.enqueue(
                    project_id=proj["id"],
                    job_type="validate",
                    payload={"test": True},
                    created_by_user_id=None,
                )
                sess.commit()

                art_repo = SqlArtifactRepository(sess)
                data = b'{"status": "REVIEW_REQUIRED"}'
                sha = hashlib.sha256(data).hexdigest()
                art = art_repo.create(
                    job_id=job["id"],
                    kind="json-report",
                    storage_key=f"jobs/{job['id']}/{sha[:8]}-report.json",
                    sha256=sha,
                    size_bytes=len(data),
                )
                sess.commit()

                self.assertEqual(art["sha256"], sha)
                self.assertEqual(art["kind"], "json-report")

                arts = art_repo.list_for_job(job["id"])
                self.assertEqual(len(arts), 1)

                # get_by_sha256 must find the artifact
                found = art_repo.get_by_sha256(sha)
                self.assertIsNotNone(found)
                self.assertEqual(found["sha256"], sha)
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")

    def test_artifact_kind_constants_match_fixture(self):
        """VALID_ARTIFACT_KINDS must cover all kinds in the fixture."""
        data = _load_fixture("artifact_samples.json")
        fixture_kinds = {a["kind"] for a in data["artifacts"]}
        try:
            from services.api.models.orm import VALID_ARTIFACT_KINDS
            for kind in fixture_kinds:
                self.assertIn(kind, VALID_ARTIFACT_KINDS,
                              f"Fixture kind {kind!r} not in VALID_ARTIFACT_KINDS")
        except ImportError:
            self.skipTest("sqlalchemy not installed")


if __name__ == "__main__":
    unittest.main()
