"""Typed command envelopes and schema-level validation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


OPERATIONS = (
    "create-project",
    "add-level",
    "add-space",
    "resize-space",
    "add-wall",
    "split-wall",
    "move-opening",
    "resize-opening",
    "add-window",
    "add-stair",
    "set-site-orientation",
    "set-program-requirement",
    "apply-furniture-operation",
)


def finding(
    *,
    rule: str,
    message: str,
    severity: str = "ERROR",
    object_ids: list[str] | None = None,
    evidence: Mapping[str, Any] | None = None,
    professional_review_required: bool = False,
) -> dict[str, Any]:
    return {
        "schemaVersion": "advocate-chambers.finding.v1",
        "id": f"command-{rule.lower().replace('_', '-')}",
        "severity": severity,
        "status": "OPEN",
        "rule": rule,
        "message": message,
        "objectIds": list(dict.fromkeys(object_ids or [])),
        "evidence": dict(evidence or {}),
        "professionalReviewRequired": professional_review_required,
    }


class CommandValidationError(ValueError):
    """Raised when an envelope cannot enter the command pipeline."""

    def __init__(self, message: str, findings: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.findings = findings or [
            finding(rule="COMMAND_SCHEMA", message=message, severity="BLOCKER")
        ]


@dataclass(frozen=True)
class CommandEnvelope:
    schema_version: str
    command_id: str
    project_id: str
    base_revision: int
    author_id: str
    operation: str
    parameters: dict[str, Any]
    idempotency_key: str
    reason: str | None = None
    source: str = "user"
    client_timestamp: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CommandEnvelope":
        required = (
            "schemaVersion",
            "commandId",
            "projectId",
            "baseRevision",
            "authorId",
            "operation",
            "parameters",
            "idempotencyKey",
        )
        missing = [key for key in required if key not in raw]
        if missing:
            raise CommandValidationError(f"missing command fields: {', '.join(missing)}")
        values = {
            "schema_version": raw["schemaVersion"],
            "command_id": raw["commandId"],
            "project_id": raw["projectId"],
            "base_revision": raw["baseRevision"],
            "author_id": raw["authorId"],
            "operation": raw["operation"],
            "parameters": raw["parameters"],
            "idempotency_key": raw["idempotencyKey"],
            "reason": raw.get("reason"),
            "source": raw.get("source", "user"),
            "client_timestamp": raw.get("clientTimestamp"),
        }
        if values["schema_version"] != "advocate-chambers.command.v1":
            raise CommandValidationError("unsupported command schema version")
        if not isinstance(values["command_id"], str) or not values["command_id"]:
            raise CommandValidationError("commandId must be a non-empty string")
        if not isinstance(values["project_id"], str) or not values["project_id"].startswith("proj-"):
            raise CommandValidationError("projectId must start with 'proj-'")
        if not isinstance(values["base_revision"], int) or isinstance(values["base_revision"], bool):
            raise CommandValidationError("baseRevision must be an integer")
        if values["base_revision"] < 1:
            raise CommandValidationError("baseRevision must be at least 1")
        if not isinstance(values["author_id"], str) or not values["author_id"]:
            raise CommandValidationError("authorId must be a non-empty string")
        if values["operation"] not in OPERATIONS:
            raise CommandValidationError(f"unsupported operation: {values['operation']}")
        if not isinstance(values["parameters"], dict) or not values["parameters"]:
            raise CommandValidationError("parameters must be a non-empty object")
        if not isinstance(values["idempotency_key"], str) or len(values["idempotency_key"]) < 8:
            raise CommandValidationError("idempotencyKey must contain at least 8 characters")
        if values["source"] not in {"user", "generator", "import", "system"}:
            raise CommandValidationError("source must be user, generator, import, or system")
        return cls(**values)

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "commandId": self.command_id,
            "projectId": self.project_id,
            "baseRevision": self.base_revision,
            "authorId": self.author_id,
            "operation": self.operation,
            "parameters": self.parameters,
            "idempotencyKey": self.idempotency_key,
            "source": self.source,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.client_timestamp is not None:
            result["clientTimestamp"] = self.client_timestamp
        return result


def command_fingerprint(command: CommandEnvelope) -> str:
    """Fingerprint the request payload, excluding only the idempotency key."""

    payload = command.to_mapping()
    payload.pop("idempotencyKey", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()