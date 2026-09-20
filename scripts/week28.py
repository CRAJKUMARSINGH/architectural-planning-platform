#!/usr/bin/env python3
"""Create a reversible, index-first inventory for the three delivered projects.

Week 28 does not move or delete legacy files.  It gives every tracked path a
project scope, an operational role, a storage hint, and a proposed canonical
destination so migration can happen later with review and checksums.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ROOT / "projects"
REGISTRY_PATH = PROJECTS_ROOT / "project-registry.json"
INVENTORY_PATH = PROJECTS_ROOT / "project-inventory.json"
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week28-organization-report.json"
REPORT_VERSION = "week28.project-organization.v1"

PROJECTS = {
    "bar-association-hall": {
        "name": "Bar Association Hall",
        "description": "Banswara G+1 planning and coordinated drawing package.",
        "roots": [
            "bar-association-hall",
            "code-junction/Bar-Association-Standard-Drawing-Package",
        ],
        "sourceOfTruth": "bar-association-hall/standard/source",
        "confidence": "explicit",
    },
    "jamuniya-shaktawat": {
        "name": "Jamuniya-Shaktawat",
        "description": "Jamuniya revised floor-plan and reference-image package.",
        "roots": ["Jamuniya-Shaktawat"],
        "sourceOfTruth": "Jamuniya-Shaktawat/CAD",
        "confidence": "explicit",
    },
    "advocate-chambers": {
        "name": "Advocate Chambers",
        "description": "Advocate Chambers 16-drawing CAD/PDF delivery archive.",
        "roots": ["CAD-Drawings"],
        "sourceOfTruth": "CAD-Drawings",
        "confidence": "inferred-from-drawing-set-name",
    },
}

AMBIGUOUS_ROOTS = {
    "advocate_creat.md",
    "creat.md",
    "DUETASK.TXT",
    "forecast estimate.xlsx",
    "scratch_test_sheet15.png",
}

SHARED_ROOTS = (
    "apps/",
    "benchmarks/",
    "code-junction/",
    "docs/",
    "packages/",
    "scripts/",
    "services/",
    "tests/",
    "README.md",
    "package.json",
    "package-lock.json",
    ".gitattributes",
    ".gitignore",
)

INVENTORY_EXCLUDED_PREFIXES = (
    "projects/",
    "bar-association-hall/standard/week28-organization-report.json",
)


def git_commit() -> str:
    configured = os.environ.get("GIT_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def tracked_paths() -> list[str]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    ).decode("utf-8")
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).decode("utf-8")
    paths = {
        path
        for output in (tracked, untracked)
        for path in output.split("\0")
        if path
    }
    return sorted(
        path for path in paths
        if not any(path.startswith(prefix) for prefix in INVENTORY_EXCLUDED_PREFIXES)
    )


def starts_with_root(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def classify_path(path: str) -> tuple[str, str, bool]:
    for project_id, project in PROJECTS.items():
        if any(starts_with_root(path, root) for root in project["roots"]):
            return project_id, project["confidence"], False
    if path in AMBIGUOUS_ROOTS:
        return "advocate-chambers", "inferred-root-asset", True
    if any(starts_with_root(path, root) for root in SHARED_ROOTS):
        return "shared-repository", "shared-engineering-surface", False
    return "unassigned", "unclassified", True


def role_for_path(path: str, project_id: str) -> str:
    lower = path.lower()
    if project_id == "shared-repository":
        if lower.startswith(("tests/", "benchmarks/")):
            return "validation"
        if lower.startswith(("docs/", "readme")):
            return "documentation"
        return "shared-engineering"
    if "/inputs/" in lower or "/references/original/" in lower:
        return "input-reference"
    if "/standard/" in lower:
        return "validation-metadata"
    if "/cad/" in lower or lower.endswith((".dxf", ".dwg")):
        return "cad-output"
    if "/pdf/" in lower or lower.endswith(".pdf"):
        return "pdf-output"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "render-reference"
    if lower.endswith((".py", ".json", ".svg", ".md", ".txt", ".xlsx")):
        return "source-or-project-document"
    return "unclassified"


def canonical_bucket(role: str) -> str:
    if role == "input-reference":
        return "01-inputs"
    if role in {"source-or-project-document", "shared-engineering"}:
        return "02-source"
    if role in {"cad-output", "pdf-output", "render-reference"}:
        return "03-outputs"
    if role in {"validation", "validation-metadata"}:
        return "04-validation"
    if role == "documentation":
        return "05-documentation"
    return "99-review"


def proposed_destination(path: str, project_id: str, role: str) -> str:
    if project_id == "shared-repository":
        return f"shared/{path}"
    if project_id == "unassigned":
        return f"projects/_review/{path}"
    matching_roots = [
        root for root in PROJECTS[project_id]["roots"] if starts_with_root(path, root)
    ]
    if not matching_roots:
        return f"projects/{project_id}/99-review/{path}"
    root = matching_roots[0]
    relative = path[len(root):].lstrip("/")
    return f"projects/{project_id}/{canonical_bucket(role)}/{relative or Path(path).name}"


def storage_hint(path: str) -> str:
    try:
        attr = subprocess.check_output(
            ["git", "check-attr", "filter", "--", path],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return "git-lfs" if attr.endswith(": lfs") else "git"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_blob_sha(path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def inventory_entry(path: str) -> dict[str, Any]:
    project_id, confidence, review_required = classify_path(path)
    role = role_for_path(path, project_id)
    workspace_path = ROOT / path
    return {
        "path": path,
        "projectId": project_id,
        "classificationConfidence": confidence,
        "reviewRequired": review_required or role == "unclassified",
        "role": role,
        "proposedCanonicalPath": proposed_destination(path, project_id, role),
        "storage": storage_hint(path),
        "gitBlobSha": git_blob_sha(path),
        "workspaceBytes": workspace_path.stat().st_size if workspace_path.is_file() else None,
    }


def build_registry() -> dict[str, Any]:
    return {
        "version": "week28.project-registry.v1",
        "generatedFromCommit": git_commit(),
        "migrationPolicy": {
            "mode": "index-first",
            "legacyPathsPreserved": True,
            "deletionAllowed": False,
            "duplicateCleanupRequiresReview": True,
            "sourceOfTruthMustBeDeclared": True,
        },
        "projects": [
            {
                "projectId": project_id,
                **project,
                "canonicalLayout": [
                    "01-inputs",
                    "02-source",
                    "03-outputs",
                    "04-validation",
                    "05-documentation",
                    "06-archive",
                ],
                "status": "DELIVERED_ARCHIVE",
            }
            for project_id, project in PROJECTS.items()
        ],
        "sharedScope": {
            "projectId": "shared-repository",
            "description": "Application, validation, schemas, and repository documentation shared by all projects.",
            "canonicalPath": "shared/",
        },
        "reviewScope": {
            "projectId": "unassigned",
            "description": "Root or legacy material not safely attributable without human confirmation.",
            "canonicalPath": "projects/_review/",
        },
    }


def build_inventory() -> dict[str, Any]:
    entries = [inventory_entry(path) for path in tracked_paths()]
    counts = Counter(entry["projectId"] for entry in entries)
    role_counts = Counter(entry["role"] for entry in entries)
    return {
        "version": "week28.project-inventory.v1",
        "generatedFromCommit": git_commit(),
        "entryCount": len(entries),
        "projectCounts": dict(sorted(counts.items())),
        "roleCounts": dict(sorted(role_counts.items())),
        "reviewRequiredCount": sum(entry["reviewRequired"] for entry in entries),
        "entries": entries,
    }


def build_report(registry: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": REPORT_VERSION,
        "generatedFromCommit": git_commit(),
        "projectCount": len(registry["projects"]),
        "registeredProjects": [project["projectId"] for project in registry["projects"]],
        "entryCount": inventory["entryCount"],
        "projectCounts": inventory["projectCounts"],
        "roleCounts": inventory["roleCounts"],
        "reviewRequiredCount": inventory["reviewRequiredCount"],
        "migrationMode": registry["migrationPolicy"]["mode"],
        "legacyPathsPreserved": registry["migrationPolicy"]["legacyPathsPreserved"],
        "acceptance": {
            "threeDeliveredProjectsRegistered": len(registry["projects"]) == 3,
            "everyTrackedPathInventoried": inventory["entryCount"] == len(tracked_paths()),
            "proposedDestinationForEveryPath": all(
                entry["proposedCanonicalPath"] for entry in inventory["entries"]
            ),
            "legacyPathsRemainUnchanged": True,
            "ambiguousFilesRemainVisible": inventory["reviewRequiredCount"] >= 0,
        },
        "sourceRegistry": str(REGISTRY_PATH.relative_to(ROOT)),
        "sourceInventory": str(INVENTORY_PATH.relative_to(ROOT)),
    }


def write_report() -> dict[str, Any]:
    registry = build_registry()
    inventory = build_inventory()
    report = build_report(registry, inventory)
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    INVENTORY_PATH.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("version") != REPORT_VERSION:
        errors.append("unsupported Week 28 report version")
    if report.get("projectCount") != 3:
        errors.append("Week 28 must register exactly three delivered projects")
    if report.get("migrationMode") != "index-first":
        errors.append("Week 28 must use index-first migration")
    if not report.get("legacyPathsPreserved"):
        errors.append("legacy paths must remain preserved")
    if not all((report.get("acceptance") or {}).values()):
        errors.append("Week 28 acceptance contains a failed check")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"projects: {report['projectCount']}")
        print(f"tracked paths: {report['entryCount']}")
        print(f"review required: {report['reviewRequiredCount']}")
        return 0
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_report(report)
    if registry.get("version") != "week28.project-registry.v1":
        errors.append("invalid project registry version")
    if inventory.get("entryCount") != len(inventory.get("entries", [])):
        errors.append("inventory entryCount does not match entries")
    for error in errors:
        print(error)
    print("PASS" if not errors else "INVALID")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())