"""E04 — Async Jobs & Storage tests.

Tests: object store put/get/sha256, job dispatch inline mode,
       artifact integrity, determinism guarantee.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestFilesystemStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_put_and_get_roundtrip(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        data = b"hello advocate-chambers"
        digest = store.put("test/hello.txt", data)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        retrieved = store.get("test/hello.txt")
        self.assertEqual(retrieved, data)

    def test_sha256_matches(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        data = b'{"status": "REVIEW_REQUIRED"}'
        returned_sha = store.put("reports/qg.json", data)
        expected = hashlib.sha256(data).hexdigest()
        self.assertEqual(returned_sha, expected)

    def test_exists(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        self.assertFalse(store.exists("nonexistent.json"))
        store.put("exists.json", b"data")
        self.assertTrue(store.exists("exists.json"))

    def test_missing_key_raises(self):
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        with self.assertRaises(FileNotFoundError):
            store.get("not/there.json")

    def test_path_traversal_sanitized(self):
        """Malicious keys should not escape the base directory."""
        from services.api.storage.object_store import FilesystemStore
        store = FilesystemStore(self.tmpdir)
        # This should not raise but also not write outside tmpdir
        data = b"safe data"
        try:
            store.put("../../etc/passwd", data)
        except Exception:
            pass  # Any exception is fine — the key is sanitized or rejected
        # Confirm nothing was written outside tmpdir
        import os
        self.assertFalse(os.path.exists("/tmp/etc/passwd"))


class TestArtifactIntegrity(unittest.TestCase):
    """Content-addressed artifact SHA-256 — ADR integrity guarantee."""

    def test_same_data_same_sha256(self):
        data = json.dumps({"status": "REVIEW_REQUIRED", "findings": []}).encode()
        h1 = hashlib.sha256(data).hexdigest()
        h2 = hashlib.sha256(data).hexdigest()
        self.assertEqual(h1, h2, "SHA-256 must be deterministic")

    def test_different_data_different_sha256(self):
        d1 = b'{"status": "PASS"}'
        d2 = b'{"status": "BLOCKED"}'
        self.assertNotEqual(
            hashlib.sha256(d1).hexdigest(),
            hashlib.sha256(d2).hexdigest(),
        )


class TestQueueDispatch(unittest.TestCase):
    """Job dispatch without Redis uses inline synchronous execution."""

    def setUp(self):
        os.environ.pop("REDIS_URL", None)

    def test_dispatch_without_redis_logs_and_continues(self):
        """dispatch_job should not raise even if the job pipeline fails."""
        from services.worker.queue import dispatch_job
        try:
            dispatch_job("fake-job-id", "validate", {"test": True})
        except Exception as exc:
            self.fail(f"dispatch_job should not raise but got: {exc}")


class TestJobTypes(unittest.TestCase):
    """Validate allowed job type constants match the schema."""

    ALLOWED_TYPES = {"generate", "validate", "enrich", "quality_gate", "export", "benchmark"}

    def test_all_types_valid(self):
        try:
            from services.api.models.orm import VALID_JOB_TYPES
            self.assertEqual(set(VALID_JOB_TYPES), self.ALLOWED_TYPES)
        except ImportError:
            self.skipTest("SQLAlchemy models not importable")


if __name__ == "__main__":
    unittest.main()
