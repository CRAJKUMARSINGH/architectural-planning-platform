"""
Sketch of a repository pattern for Advocate-Chambers FastAPI service.
This is illustrative — adapt to the real SQLAlchemy/SQLModel models.
"""

from __future__ import annotations

from typing import Protocol, Any
from uuid import UUID


class ProjectRepository(Protocol):
    def get(self, project_id: UUID) -> dict[str, Any] | None: ...
    def create(self, org_id: UUID, name: str, units: str) -> dict[str, Any]: ...
    def list_for_org(self, org_id: UUID) -> list[dict[str, Any]]: ...


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
    ) -> dict[str, Any]: ...

    def get(self, revision_id: UUID) -> dict[str, Any] | None: ...
    def list_for_project(self, project_id: UUID) -> list[dict[str, Any]]: ...


class JobRepository(Protocol):
    def enqueue(
        self,
        project_id: UUID,
        job_type: str,
        payload: dict[str, Any],
        created_by_user_id: UUID | None,
        revision_id: UUID | None = None,
    ) -> dict[str, Any]: ...

    def update_status(
        self,
        job_id: UUID,
        status: str,
        progress: int | None = None,
        error: str | None = None,
    ) -> None: ...

    def get(self, job_id: UUID) -> dict[str, Any] | None: ...


class ArtifactRepository(Protocol):
    def create(
        self,
        job_id: UUID,
        kind: str,
        storage_key: str,
        sha256: str,
        size_bytes: int | None = None,
    ) -> dict[str, Any]: ...

    def list_for_job(self, job_id: UUID) -> list[dict[str, Any]]: ...


# FastAPI dependency example (pseudo):
#
# def get_project_repo(session: Session = Depends(get_session)) -> ProjectRepository:
#     return SqlProjectRepository(session)
