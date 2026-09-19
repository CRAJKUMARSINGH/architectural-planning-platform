import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week26 import (  # noqa: E402
    _baseline_model,
    compare_revisions,
    recover_last_valid_revision,
    verify_package,
    write_package,
)


class Week26ReproducibilityTests(unittest.TestCase):
    def test_package_round_trips_and_verifies(self):
        with tempfile.TemporaryDirectory(prefix="week26-test-") as temp_dir:
            package = Path(temp_dir) / "package"
            metadata = write_package(package)
            self.assertTrue(metadata["modelSignature"])
            self.assertEqual(verify_package(package), [])

    def test_tampered_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="week26-test-") as temp_dir:
            package = Path(temp_dir) / "package"
            write_package(package)
            manifest_path = package / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["artifacts"][0]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest))
            errors = verify_package(package)
            self.assertTrue(any("manifest signature mismatch" in error for error in errors))

    def test_missing_artifact_is_explicit(self):
        with tempfile.TemporaryDirectory(prefix="week26-test-") as temp_dir:
            package = Path(temp_dir) / "package"
            write_package(package)
            (package / "validation-findings.json").unlink()
            errors = verify_package(package)
            self.assertTrue(any("missing artifact" in error for error in errors))

    def test_partial_generation_preserves_last_valid_revision(self):
        current = {
            "revisionId": "REV-001",
            "state": "VALID",
            "modelSignature": "model",
            "validationSignature": "validation",
        }
        partial = {**current, "revisionId": "REV-002", "state": "PARTIAL"}
        self.assertEqual(recover_last_valid_revision(current, partial), current)

    def test_revision_comparison_reports_differences(self):
        current = {"modelSignature": "a", "validationSignature": "b", "inputModelSha256": "c", "rulePackVersion": "v1"}
        changed = {**current, "validationSignature": "changed"}
        comparison = compare_revisions(current, changed)
        self.assertFalse(comparison["same"])
        self.assertEqual(comparison["differences"], ["validationSignature"])


if __name__ == "__main__":
    unittest.main()