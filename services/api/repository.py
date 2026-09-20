"""
Advocate-Chambers — Repository Pattern (Sketch)
================================================
Protocol interfaces for the persistence layer.
Real implementations using SQLAlchemy/SQLModel are added in E02.

These protocols:
- Define the contract between FastAPI route handlers and the DB layer.
- Allow easy mocking in unit tests without a live database.
- Enforce the data-access rules from ADR-001 (geometry = blobs only) and
  ADR-003 (org isolation at query layer).

Usage in FastAPI:
    from services.api.repository import ProjectRepository
    ...
    def get_project_repo(session: Session = Depends(get_session)) -> ProjectRepository:
        from services.api.repository_sql import SqlProjectRepository
        return SqlProjectRepository(session)
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectRepository(Protocol):
    def get(self, project_id: UUID, org_id: UUID) -> dict[str, Any] | None:
        """Return a project only if it belongs to the given org (ADR-003)."""
        ...

    def create(
        self,
        org_id: UUID,
        name: str,
        units: str = "inch",
        created_by_user_id: UUID | None = None,
    ) -> dict[str, Any]: ...

    def list_for_org(self, org_id: UUID) -> list[dict[str, Any]]: ...

    def soft_delete(self, project_id: UUID, org_id: UUID) -> None: ...


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------
class RevisionRepository(Protocol):
    def create(
        self,
        project_id: UUID,
        revision_number: int,
        model_sha256: str,
        model_storage_key: str,
        author_user_id: UUID | None,
        reason: str,
        rule_pack_version: str | None = None,
        parent_revision_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Create a revision metadata record.
        The actual geometry bytes must already be uploaded to object store
        BEFORE calling this — model_sha256 is the content address.
        See ADR-001.
        """
        ...

    def get(self, revision_id: UUID) -> dict[str, Any] | None: ...
    def list_for_project(self, project_id: UUID) -> list[dict[str, Any]]: ...

    def set_validation_report_sha256(
        self, revision_id: UUID, sha256: str
    ) -> None: ...


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
class JobRepository(Protocol):
    def enqueue(
        self,
        project_id: UUID,
        job_type: str,
        payload: dict[str, Any],
        created_by_user_id: UUID | None,
        revision_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Persist a new job in 'queued' state and return its record."""
        ...

    def update_status(
        self,
        job_id: UUID,
        status: str,
        progress: int | None = None,
        error: str | None = None,
    ) -> None: ...

    def get(self, job_id: UUID) -> dict[str, Any] | None: ...
    def list_for_project(self, project_id: UUID) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------
class ArtifactRepository(Protocol):
    def create(
        self,
        job_id: UUID,
        kind: str,
        storage_key: str,
        sha256: str,
        size_bytes: int | None = None,
    ) -> dict[str, Any]:
        """
        Record artifact metadata after it has been written to object store.
        sha256 is the content address — verify before inserting.
        """
        ...

    def list_for_job(self, job_id: UUID) -> list[dict[str, Any]]: ...
    def get_by_sha256(self, sha256: str) -> dict[str, Any] | None: ...


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
class AuditRepository(Protocol):
    def record(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        organization_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        Append an immutable audit event.
        Never update or delete audit rows — append-only.
        """
        ...

    def list_for_org(
        self,
        org_id: UUID,
        limit: int = 100,
        before_id: UUID | None = None,
    ) -> list[dict[str, Any]]: ...
