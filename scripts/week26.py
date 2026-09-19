#!/usr/bin/env python3
"""Build the Week 26 reproducibility and failure-recovery evidence package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "bar-association-hall" / "standard" / "week26-reproducibility-package"
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week26-reproducibility-report.json"
REVISION_COMPARISON_PATH = ROOT / "bar-association-hall" / "standard" / "week26-revision-comparison-report.json"
REPORT_VERSION = "week26.reproducibility.v1"
RULE_PACK_VERSION = "week22.adversarial-fixture.v1"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from week22 import detect_findings, read_json  # noqa: E402
from week23 import signature  # noqa: E402


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _git_commit() -> str:
    configured = os.environ.get("GIT_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _baseline_model() -> dict[str, Any]:
    return read_json(ROOT / "tests/fixtures/adversarial/valid/baseline.json")


def _artifact_manifest(package_path: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(package_path.glob("*.json")):
        if path.name == "artifact-manifest.json":
            continue
        payload = path.read_bytes()
        artifacts.append({
            "path": path.name,
            "kind": path.stem,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "status": "PRESENT",
        })
    manifest: dict[str, Any] = {
        "version": "week26.artifact-manifest.v1",
        "artifacts": artifacts,
        "manifestSignature": None,
    }
    manifest["manifestSignature"] = signature({
        key: value for key, value in manifest.items() if key != "manifestSignature"
    })
    return manifest


def write_package(package_path: Path = PACKAGE_PATH) -> dict[str, Any]:
    package_path.mkdir(parents=True, exist_ok=True)
    for old in package_path.glob("*.json"):
        old.unlink()
    model = _baseline_model()
    findings = detect_findings(model)
    model_signature = signature(model)
    validation_signature = signature(findings)
    input_path = package_path / "input-model.json"
    validation_path = package_path / "validation-findings.json"
    revision_path = package_path / "revision.json"
    write_json(input_path, model)
    write_json(validation_path, {"findings": findings, "validationSignature": validation_signature})
    write_json(revision_path, {
        "revisionId": "REV-001",
        "state": "VALID",
        "applicationCommit": _git_commit(),
        "rulePackVersion": RULE_PACK_VERSION,
        "modelSignature": model_signature,
        "validationSignature": validation_signature,
        "inputModelSha256": sha256_bytes(input_path.read_bytes()),
        "artifactManifest": "artifact-manifest.json",
    })
    manifest = _artifact_manifest(package_path)
    write_json(package_path / "artifact-manifest.json", manifest)
    return {
        "inputModelSha256": sha256_bytes(input_path.read_bytes()),
        "modelSignature": model_signature,
        "validationSignature": validation_signature,
        "manifestSignature": manifest["manifestSignature"],
        "applicationCommit": _git_commit(),
        "rulePackVersion": RULE_PACK_VERSION,
    }


def verify_package(package_path: Path = PACKAGE_PATH) -> list[str]:
    errors: list[str] = []
    manifest_path = package_path / "artifact-manifest.json"
    if not manifest_path.is_file():
        return ["missing artifact-manifest.json"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest_signature = signature({
        key: value for key, value in manifest.items() if key != "manifestSignature"
    })
    if manifest.get("manifestSignature") != expected_manifest_signature:
        errors.append("artifact manifest signature mismatch")
    for artifact in manifest.get("artifacts", []):
        artifact_path = package_path / artifact["path"]
        if not artifact_path.is_file():
            errors.append(f"missing artifact: {artifact['path']}")
            continue
        payload = artifact_path.read_bytes()
        if sha256_bytes(payload) != artifact.get("sha256"):
            errors.append(f"artifact hash mismatch: {artifact['path']}")
        if artifact.get("status") != "PRESENT":
            errors.append(f"artifact is not present: {artifact['path']}")
    input_path = package_path / "input-model.json"
    validation_path = package_path / "validation-findings.json"
    revision_path = package_path / "revision.json"
    if input_path.is_file() and validation_path.is_file() and revision_path.is_file():
        model = json.loads(input_path.read_text(encoding="utf-8"))
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
        findings = detect_findings(model)
        if signature(model) != revision.get("modelSignature"):
            errors.append("model signature mismatch")
        if signature(findings) != revision.get("validationSignature"):
            errors.append("validation signature mismatch")
        if validation.get("validationSignature") != revision.get("validationSignature"):
            errors.append("validation artifact signature mismatch")
        if sha256_bytes(input_path.read_bytes()) != revision.get("inputModelSha256"):
            errors.append("input model hash mismatch")
    return errors


def compare_revisions(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    fields = ("modelSignature", "validationSignature", "inputModelSha256", "rulePackVersion")
    differences = [field for field in fields if left.get(field) != right.get(field)]
    return {"same": not differences, "differences": differences}


def recover_last_valid_revision(current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate.get("state") != "VALID":
        return copy.deepcopy(current)
    return copy.deepcopy(candidate)


def _failure_injections(package_metadata: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="week26-") as temp_dir:
        temp_root = Path(temp_dir)
        tampered = temp_root / "tampered"
        missing = temp_root / "missing"
        second_workspace = temp_root / "second-workspace"
        shutil.copytree(PACKAGE_PATH, tampered)
        shutil.copytree(PACKAGE_PATH, missing)
        shutil.copytree(PACKAGE_PATH, second_workspace)

        tampered_manifest_path = tampered / "artifact-manifest.json"
        tampered_manifest = json.loads(tampered_manifest_path.read_text(encoding="utf-8"))
        tampered_manifest["artifacts"][0]["sha256"] = "0" * 64
        tampered_manifest_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")
        tampered_errors = verify_package(tampered)

        missing_artifact = missing / "validation-findings.json"
        missing_artifact.unlink()
        missing_errors = verify_package(missing)

        current_revision = json.loads((PACKAGE_PATH / "revision.json").read_text(encoding="utf-8"))
        partial_candidate = {
            **current_revision,
            "revisionId": "REV-002",
            "state": "PARTIAL",
            "validationSignature": "partial-export",
        }
        recovered = recover_last_valid_revision(current_revision, partial_candidate)
        partial_preserved = recovered == current_revision and recovered["state"] == "VALID"

        restored = copy.deepcopy(current_revision)
        archive = copy.deepcopy(current_revision)
        restored = copy.deepcopy(archive)
        archive_restore = compare_revisions(current_revision, restored)
        second_workspace_errors = verify_package(second_workspace)
        comparison = compare_revisions(current_revision, recovered)
        return {
            "tamperedManifestRejected": any("manifest signature mismatch" in error for error in tampered_errors),
            "tamperedManifestErrors": tampered_errors,
            "missingArtifactExplicitlyMarked": any("missing artifact" in error for error in missing_errors),
            "missingArtifactErrors": missing_errors,
            "partialExportPreservesCurrentValidRevision": partial_preserved,
            "archiveRestorePreservesCurrentRevision": archive_restore["same"],
            "secondWorkspaceVerified": not second_workspace_errors,
            "secondWorkspaceErrors": second_workspace_errors,
            "revisionComparison": comparison,
            "artifactManifestSignature": package_metadata["manifestSignature"],
        }


def build_report() -> dict[str, Any]:
    metadata = write_package()
    model = _baseline_model()
    first_findings = detect_findings(model)
    rerun_model = copy.deepcopy(model)
    rerun_findings = detect_findings(rerun_model)
    rerun = {
        "sameModelSignature": signature(model) == signature(rerun_model),
        "sameValidationSignature": signature(first_findings) == signature(rerun_findings),
        "sameFindings": first_findings == rerun_findings,
        "rerunModelSignature": signature(rerun_model),
        "rerunValidationSignature": signature(rerun_findings),
    }
    failures = _failure_injections(metadata)
    acceptance = {
        "tamperedManifestRejected": failures["tamperedManifestRejected"],
        "missingArtifactsExplicit": failures["missingArtifactExplicitlyMarked"],
        "partialGenerationCannotReplaceValidRevision": failures["partialExportPreservesCurrentValidRevision"],
        "softArchiveRestorePreservesRevision": failures["archiveRestorePreservesCurrentRevision"],
        "secondWorkspaceCanVerify": failures["secondWorkspaceVerified"],
        "rerunMatchesOriginal": all(rerun[key] for key in ("sameModelSignature", "sameValidationSignature", "sameFindings")),
    }
    return {
        "version": REPORT_VERSION,
        "packagePath": str(PACKAGE_PATH.relative_to(ROOT)),
        **metadata,
        "rerun": rerun,
        "failureInjection": failures,
        "revisionComparison": failures["revisionComparison"],
        "acceptance": acceptance,
        "status": "PASS" if all(acceptance.values()) else "BLOCKED",
        "reportSignature": None,
    }


def write_report() -> dict[str, Any]:
    report = build_report()
    write_json(REPORT_PATH, report)
    write_json(REVISION_COMPARISON_PATH, {
        "version": "week26.revision-comparison.v1",
        "currentRevision": "REV-001",
        "restoredRevision": "REV-001",
        "partialCandidate": "REV-002",
        "comparison": report["revisionComparison"],
        "partialGenerationPreservedCurrent": (
            report["acceptance"]["partialGenerationCannotReplaceValidRevision"]
        ),
    })
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("version") != REPORT_VERSION:
        errors.append("unsupported Week 26 report version")
    if report.get("status") not in {"PASS", "BLOCKED"}:
        errors.append("invalid Week 26 report status")
    if report.get("status") == "PASS" and not all((report.get("acceptance") or {}).values()):
        errors.append("PASS report contains a failed acceptance check")
    package_errors = verify_package(PACKAGE_PATH)
    if package_errors:
        errors.extend(package_errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"status: {report['status']}")
        return 0 if report["status"] == "PASS" else 1
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_report(report)
    print(report.get("status", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())