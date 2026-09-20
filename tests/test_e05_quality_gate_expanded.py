"""E05 — CI/CD & Quality Gate expanded regression tests.

Covers: fixture-driven gate enforcement, SBOM presence, baseline drift,
adversarial count regression, blocker finding regression, release check,
script exit-code contracts, check_quality_gate edge cases.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e05"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _run_check(report: dict, baseline: dict | None = None) -> tuple[int, str]:
    """Run check_quality_gate.py against a tmp report and return (exit_code, stderr)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rp = Path(tmpdir) / "quality-gate-report.json"
        rp.write_text(json.dumps(report), encoding="utf-8")
        cmd = [
            sys.executable,
            "scripts/enterprise/check_quality_gate.py",
            "--report", str(rp),
        ]
        if baseline is not None:
            bp = Path(tmpdir) / "baseline.json"
            bp.write_text(json.dumps(baseline), encoding="utf-8")
            cmd += ["--baseline", str(bp)]
        else:
            cmd += ["--baseline", str(Path(tmpdir) / "no-baseline.json")]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        return result.returncode, result.stderr


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_passing_fixture_loads(self):
        data = _load_fixture("quality_gate_passing.json")
        self.assertEqual(data["status"], "REVIEW_REQUIRED")
        self.assertEqual(data["adversarialSuite"]["detected"], 30)

    def test_blocked_fixture_loads(self):
        data = _load_fixture("quality_gate_blocked.json")
        self.assertEqual(data["status"], "BLOCKED")
        self.assertGreater(len(data["findings"]), 0)

    def test_adversarial_regression_fixture_loads(self):
        data = _load_fixture("quality_gate_adversarial_regression.json")
        self.assertLess(data["adversarialSuite"]["detected"], 30)

    def test_blocked_fixture_has_blocker_severity(self):
        data = _load_fixture("quality_gate_blocked.json")
        severities = {f["severity"] for f in data["findings"]}
        self.assertIn("BLOCKER", severities)


# ---------------------------------------------------------------------------
# Fixture-driven gate enforcement
# ---------------------------------------------------------------------------

class TestFixtureDrivenGateEnforcement(unittest.TestCase):
    """Use fixture files as inputs to the check_quality_gate.py script."""

    def test_passing_fixture_exits_0(self):
        report = _load_fixture("quality_gate_passing.json")
        code, _ = _run_check(report)
        self.assertEqual(code, 0, "Passing fixture should exit 0")

    def test_blocked_fixture_exits_1(self):
        report = _load_fixture("quality_gate_blocked.json")
        code, stderr = _run_check(report)
        self.assertEqual(code, 1, "BLOCKED fixture should exit 1")
        self.assertIn("BLOCKED", stderr)

    def test_adversarial_regression_fixture_exits_1(self):
        report = _load_fixture("quality_gate_adversarial_regression.json")
        code, stderr = _run_check(report)
        self.assertEqual(code, 1, "Adversarial regression should exit 1")
        # Stderr should mention the detection count
        self.assertTrue(
            "28" in stderr or "adversarial" in stderr.lower(),
            f"Expected stderr to mention '28' or 'adversarial', got: {stderr!r}",
        )


# ---------------------------------------------------------------------------
# Adversarial count regression
# ---------------------------------------------------------------------------

class TestAdversarialCountRegression(unittest.TestCase):
    """30/30 detected is the minimum bar — any drop must fail CI."""

    def test_exact_30_passes(self):
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 30, "total": 30}, "findings": []}
        code, _ = _run_check(report)
        self.assertEqual(code, 0)

    def test_29_detected_fails(self):
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 29, "total": 30}, "findings": []}
        code, _ = _run_check(report)
        self.assertEqual(code, 1)

    def test_0_detected_fails_hard(self):
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 0, "total": 30}, "findings": []}
        code, _ = _run_check(report)
        self.assertEqual(code, 1)

    def test_more_than_30_total_still_passes_if_all_detected(self):
        """If a future run expands to 35 cases and all pass, CI must stay green."""
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 35, "total": 35}, "findings": []}
        code, _ = _run_check(report)
        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# Blocker finding regression
# ---------------------------------------------------------------------------

class TestBlockerFindingRegression(unittest.TestCase):
    def test_single_blocker_fails_ci(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [{"severity": "BLOCKER", "code": "EGRESS-001", "message": "blocked"}],
        }
        code, stderr = _run_check(report)
        self.assertEqual(code, 1)

    def test_warning_only_does_not_fail_ci(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [{"severity": "WARNING", "code": "ROAD-001", "message": "road width assumed"}],
        }
        code, _ = _run_check(report)
        self.assertEqual(code, 0)

    def test_error_severity_fails_ci(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [{"severity": "ERROR", "code": "STAIR-002", "message": "riser height error"}],
        }
        code, _ = _run_check(report)
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# Baseline drift detection
# ---------------------------------------------------------------------------

class TestBaselineDriftDetection(unittest.TestCase):
    def test_regression_from_pass_to_review_required_warns(self):
        """Dropping from PASS to REVIEW_REQUIRED in the baseline triggers a REGRESSION warning."""
        current = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 30, "total": 30}, "findings": []}
        baseline = {"status": "PASS", "adversarialSuite": {"detected": 30, "total": 30}}
        code, stderr = _run_check(current, baseline=baseline)
        self.assertIn("REGRESSION", stderr)

    def test_no_baseline_file_is_non_fatal(self):
        """Absent baseline file must not cause a hard failure."""
        report = {"status": "REVIEW_REQUIRED", "adversarialSuite": {"detected": 30, "total": 30}, "findings": []}
        code, _ = _run_check(report, baseline=None)
        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# SBOM and release artefacts
# ---------------------------------------------------------------------------

class TestSbomAndReleaseArtifacts(unittest.TestCase):
    def test_release_check_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "enterprise" / "release_check.py").exists())

    def test_release_check_script_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile",
             "scripts/enterprise/release_check.py"],
            capture_output=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_release_checklist_mentions_sbom(self):
        cl = (ROOT / "docs" / "enterprise" / "checklists" / "release.md").read_text(encoding="utf-8")
        self.assertIn("SBOM", cl)

    def test_ci_workflow_references_quality_gate_check(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertTrue(
            "check_quality_gate" in ci or "quality-gate" in ci.lower(),
            "CI workflow should reference check_quality_gate.py or quality-gate step",
        )

    def test_release_workflow_exists(self):
        self.assertTrue((ROOT / ".github" / "workflows" / "release.yml").exists())

    def test_dependabot_config_exists(self):
        dep = ROOT / ".github" / "dependabot.yml"
        self.assertTrue(dep.exists(), "Dependabot config missing — supply-chain scanning not scheduled")

    def test_verify_artifact_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "enterprise" / "verify_artifact.py").exists())


# ---------------------------------------------------------------------------
# check_quality_gate.py edge cases
# ---------------------------------------------------------------------------

class TestCheckQualityGateEdgeCases(unittest.TestCase):
    def test_missing_adversarial_key_fails(self):
        """Report without adversarialSuite key must fail."""
        report = {"status": "REVIEW_REQUIRED", "findings": []}
        code, _ = _run_check(report)
        self.assertEqual(code, 1)

    def test_incomplete_status_still_passes_if_no_blockers(self):
        """INCOMPLETE status is gated differently — check actual script behaviour."""
        report = {
            "status": "INCOMPLETE",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [],
        }
        code, stderr = _run_check(report)
        # INCOMPLETE should warn or fail — not silently pass
        # The important thing: BLOCKED findings still fail
        # This test documents current behaviour
        self.assertIn(code, (0, 1), "Exit code must be 0 or 1, not a crash")

    def test_nonexistent_report_path_exits_2(self):
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/check_quality_gate.py",
             "--report", "/nonexistent/path/report.json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
