"""Immutable revision metadata and optimistic-locking primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .commands import CommandEnvelope, finding
from .serializers import sha256


class RevisionConflict(ValueError):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"base revision {expected} is stale; current revision is {actual}")


@dataclass(frozen=True)
class RevisionSummary:
    revision_number: int
    revision_id: str
    project_id: str
    command_id: str
    operation: str
    changed_object_ids: tuple[str, ...]
    model_sha256: str
    reason: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "revisionNumber": self.revision_number,
            "revisionId": self.revision_id,
            "projectId": self.project_id,
            "commandId": self.command_id,
            "operation": self.operation,
            "changedObjectIds": list(self.changed_object_ids),
            "modelSha256": self.model_sha256,
            "reason": self.reason,
        }


def model_revision(model: dict[str, Any] | None) -> int | None:
    if model is None:
        return None
    project = model.get("project", {})
    revision = project.get("revision")
    return revision if isinstance(revision, int) and not isinstance(revision, bool) else None


def revision_conflict_finding(expected: int, actual: int) -> dict[str, Any]:
    return finding(
        rule="REVISION_CONFLICT",
        message=f"base revision {expected} is stale; current revision is {actual}",
        severity="BLOCKER",
        evidence={"expectedBaseRevision": expected, "currentRevision": actual},
    )


def commit_revision(
    model: dict[str, Any],
    command: CommandEnvelope,
    changed_object_ids: list[str],
) -> RevisionSummary:
    current = model_revision(model)
    if current is None:
        raise ValueError("canonical model has no integer project revision")
    next_revision = current + 1
    project = model.setdefault("project", {})
    project["revision"] = next_revision
    for collection in (
        "levels",
        "spaces",
        "openings",
        "windows",
        "stairs",
        "verticalConnectors",
    ):
        for item in model.get(collection, []):
            if item.get("id") in changed_object_ids:
                item["revision"] = next_revision
    reason = command.reason or f"{command.operation} by {command.author_id}"
    model.setdefault("revisions", []).append(
        {
            "id": f"R{next_revision}",
            "date": command.client_timestamp or "1970-01-01T00:00:00+00:00",
            "author": command.author_id,
            "summary": reason,
            "source": command.source,
            "legacy": {"commandId": command.command_id, "operation": command.operation},
        }
    )
    digest = sha256(model)
    return RevisionSummary(
        revision_number=next_revision,
        revision_id=f"R{next_revision}",
        project_id=command.project_id,
        command_id=command.command_id,
        operation=command.operation,
        changed_object_ids=tuple(sorted(set(changed_object_ids))),
        model_sha256=digest,
        reason=reason,
    )