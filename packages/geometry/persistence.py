"""Durable revision transaction coordination.

This module deliberately depends only on repository and object-store
protocols.  SQLAlchemy remains an adapter concern, while the ordering and
integrity rules are testable without a live database.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Protocol


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")


class RevisionPersistenceError(RuntimeError):
    """Base error for a revision transaction that cannot be committed."""


class ProjectNotFound(RevisionPersistenceError):
    pass


class RevisionConflict(RevisionPersistenceError):
    def __init__(self, expected: int, actual: int, current_revision_id: Any = None) -> None:
        self.expected = expected
        self.actual = actual
        self.current_revision_id = current_revision_id
        super().__init__(
            f"base revision {expected} is stale; current revision is {actual}"
        )


class IdempotencyConflict(RevisionPersistenceError):
    pass


class IntegrityError(RevisionPersistenceError):
    pass


class RevisionObjectStore(Protocol):
    def put(self, key: str, data: bytes) -> str:
        """Write bytes and return their SHA-256 digest."""


class ProjectRevisionRepository(Protocol):
    def get(self, project_id: Any, org_id: Any) -> dict[str, Any] | None: ...

    def advance_current_revision(
        self,
        project_id: Any,
        org_id: Any,
        expected_current_revision_id: Any,
        new_revision_id: Any,
    ) -> bool: ...


class PersistentRevisionRepository(Protocol):
    def get(self, revision_id: Any) -> dict[str, Any] | None: ...

    def get_by_idempotency(
        self, project_id: Any, idempotency_key: str
    ) -> dict[str, Any] | None: ...

    def create(
        self,
        project_id: Any,
        revision_number: int,
        model_sha256: str,
        model_storage_key: str,
        author_user_id: Any,
        reason: str,
        rule_pack_version: str | None = None,
        parent_revision_id: Any = None,
        command_id: str | None = None,
        idempotency_key: str | None = None,
        command_fingerprint: str | None = None,
        engine_version: str = "phase2.command-engine.v1",
        validation_state: str = "DRAFT",
    ) -> dict[str, Any]: ...

    def set_validation_report_sha256(self, revision_id: Any, sha256: str) -> None: ...


class AuditRepository(Protocol):
    def record(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        organization_id: Any = None,
        actor_user_id: Any = None,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class RevisionCommitRequest:
    organization_id: Any
    project_id: Any
    base_revision: int
    model_bytes: bytes
    author_user_id: Any = None
    reason: str = "Persist canonical model revision"
    rule_pack_version: str | None = None
    command_id: str | None = None
    idempotency_key: str | None = None
    command_fingerprint: str | None = None
    engine_version: str = "phase2.command-engine.v1"
    validation_state: str = "DRAFT"
    request_id: str | None = None
    audit_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class RevisionCommitResult:
    revision: dict[str, Any]
    model_sha256: str
    model_storage_key: str
    replayed: bool = False

    def to_mapping(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "modelSha256": self.model_sha256,
            "modelStorageKey": self.model_storage_key,
            "replayed": self.replayed,
        }


def _component(value: Any, label: str) -> str:
    text = str(value)
    if not text or not _SAFE_ID.fullmatch(text):
        raise ValueError(f"{label} contains unsafe storage-key characters")
    return text


def revision_storage_key(
    organization_id: Any,
    project_id: Any,
    model_sha256: str,
    kind: str = "model",
) -> str:
    """Build the stable object-store path described by the phase-three plan."""

    if not _SHA256.fullmatch(model_sha256):
        raise ValueError("model_sha256 must be a lowercase SHA-256 digest")
    if kind not in {"model", "validation"}:
        raise ValueError("revision object kind must be model or validation")
    return (
        f"orgs/{_component(organization_id, 'organization')}/"
        f"projects/{_component(project_id, 'project')}/"
        f"revisions/{model_sha256}/{kind}.json"
    )


class RevisionTransactionCoordinator:
    """Coordinate object storage, revision metadata, CAS, and audit.

    The caller owns the database transaction.  SQL adapters should invoke
    ``commit`` inside ``session.begin()`` so a failed CAS rolls back the
    revision row while the content-addressed object remains harmlessly
    deduplicated in object storage.
    """

    def __init__(
        self,
        projects: ProjectRevisionRepository,
        revisions: PersistentRevisionRepository,
        objects: RevisionObjectStore,
        audit: AuditRepository | None = None,
    ) -> None:
        self.projects = projects
        self.revisions = revisions
        self.objects = objects
        self.audit = audit

    def commit(self, request: RevisionCommitRequest) -> RevisionCommitResult:
        if request.base_revision < 0:
            raise ValueError("base_revision cannot be negative")
        if not isinstance(request.model_bytes, bytes) or not request.model_bytes:
            raise ValueError("model_bytes must be non-empty bytes")
        if request.idempotency_key and not request.command_fingerprint:
            raise ValueError("command_fingerprint is required with idempotency_key")

        if request.idempotency_key:
            existing = self.revisions.get_by_idempotency(
                request.project_id, request.idempotency_key
            )
            if existing is not None:
                if existing.get("command_fingerprint") != request.command_fingerprint:
                    raise IdempotencyConflict(
                        "idempotency key was already used for different command parameters"
                    )
                return RevisionCommitResult(
                    revision=existing,
                    model_sha256=existing["model_sha256"],
                    model_storage_key=existing["model_storage_key"],
                    replayed=True,
                )

        project = self.projects.get(request.project_id, request.organization_id)
        if project is None:
            raise ProjectNotFound("project does not exist in the requested organization")

        current_id = project.get("current_revision_id")
        current = self.revisions.get(current_id) if current_id is not None else None
        actual_revision = int(current["revision_number"]) if current else 0
        if request.base_revision != actual_revision:
            raise RevisionConflict(request.base_revision, actual_revision, current_id)

        digest = hashlib.sha256(request.model_bytes).hexdigest()
        storage_key = revision_storage_key(
            request.organization_id, request.project_id, digest, "model"
        )
        stored_digest = self.objects.put(storage_key, request.model_bytes)
        if stored_digest != digest:
            raise IntegrityError("object store returned a digest different from the model bytes")

        revision = self.revisions.create(
            project_id=request.project_id,
            revision_number=actual_revision + 1,
            model_sha256=digest,
            model_storage_key=storage_key,
            author_user_id=request.author_user_id,
            reason=request.reason,
            rule_pack_version=request.rule_pack_version,
            parent_revision_id=current_id,
            command_id=request.command_id,
            idempotency_key=request.idempotency_key,
            command_fingerprint=request.command_fingerprint,
            engine_version=request.engine_version,
            validation_state=request.validation_state,
        )
        new_revision_id = revision["id"]
        advanced = self.projects.advance_current_revision(
            request.project_id,
            request.organization_id,
            current_id,
            new_revision_id,
        )
        if not advanced:
            latest = self.projects.get(request.project_id, request.organization_id) or {}
            latest_id = latest.get("current_revision_id")
            latest_revision = self.revisions.get(latest_id) if latest_id is not None else None
            latest_number = int(latest_revision["revision_number"]) if latest_revision else 0
            raise RevisionConflict(request.base_revision, latest_number, latest_id)

        if self.audit is not None:
            self.audit.record(
                action="revision.created",
                resource_type="revision",
                resource_id=str(new_revision_id),
                organization_id=request.organization_id,
                actor_user_id=request.author_user_id,
                payload={
                    "projectId": str(request.project_id),
                    "revisionNumber": actual_revision + 1,
                    "modelSha256": digest,
                    "commandId": request.command_id,
                    **(request.audit_payload or {}),
                },
                request_id=request.request_id,
            )
        return RevisionCommitResult(revision, digest, storage_key)

    def attach_validation_report(
        self,
        revision: dict[str, Any],
        report_bytes: bytes,
        organization_id: Any | None = None,
    ) -> tuple[str, str]:
        if not report_bytes:
            raise ValueError("report_bytes must be non-empty bytes")
        project_id = revision["project_id"]
        organization_id = organization_id or revision.get("organization_id")
        if organization_id is None:
            raise ValueError("organization_id is required to store a validation report")
        storage_key = revision_storage_key(
            organization_id,
            project_id,
            revision["model_sha256"],
            "validation",
        )
        digest = hashlib.sha256(report_bytes).hexdigest()
        stored_digest = self.objects.put(storage_key, report_bytes)
        if stored_digest != digest:
            raise IntegrityError("object store returned a digest different from the report bytes")
        self.revisions.set_validation_report_sha256(revision["id"], digest)
        return storage_key, digest