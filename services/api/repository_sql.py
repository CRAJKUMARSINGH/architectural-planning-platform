"""SQLAlchemy implementations of repository protocols — E02 Persistence.

All project/revision queries filter by org_id to enforce ADR-003 isolation.
Geometry bytes never live here — only SHA-256 pointers (ADR-001).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models.orm import Artifact, AuditEvent, Job, Project, Revision


def _row(obj: Any) -> dict[str, Any]:
    """Shallow dict from ORM object (no lazy loads)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class SqlProjectRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def get(self, project_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any] | None:
        row = self._s.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == org_id,
                Project.deleted_at.is_(None),
            )
        )
        return _row(row) if row else None

    def create(
        self,
        org_id: uuid.UUID,
        name: str,
        units: str = "inch",
        created_by_user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        proj = Project(organization_id=org_id, name=name, units=units)
        self._s.add(proj)
        self._s.flush()
        return _row(proj)

    def list_for_org(self, org_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self._s.scalars(
            select(Project).where(
                Project.organization_id == org_id,
                Project.deleted_at.is_(None),
            )
        ).all()
        return [_row(r) for r in rows]

    def soft_delete(self, project_id: uuid.UUID, org_id: uuid.UUID) -> None:
        proj = self._s.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == org_id,
            )
        )
        if proj:
            proj.deleted_at = datetime.now(timezone.utc)
            self._s.flush()

    def advance_current_revision(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        expected_current_revision_id: uuid.UUID | None,
        new_revision_id: uuid.UUID,
    ) -> bool:
        """Advance a project pointer only if it still has the expected parent."""

        statement = update(Project).where(
            Project.id == project_id,
            Project.organization_id == org_id,
            Project.deleted_at.is_(None),
        )
        if expected_current_revision_id is None:
            statement = statement.where(Project.current_revision_id.is_(None))
        else:
            statement = statement.where(
                Project.current_revision_id == expected_current_revision_id
            )
        result = self._s.execute(
            statement.values(current_revision_id=new_revision_id)
        )
        self._s.flush()
        return result.rowcount == 1


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------
class SqlRevisionRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self,
        project_id: uuid.UUID,
        revision_number: int,
        model_sha256: str,
        model_storage_key: str,
        author_user_id: uuid.UUID | None,
        reason: str,
        rule_pack_version: str | None = None,
        parent_revision_id: uuid.UUID | None = None,
        command_id: str | None = None,
        idempotency_key: str | None = None,
        command_fingerprint: str | None = None,
        engine_version: str = "phase2.command-engine.v1",
        validation_state: str = "DRAFT",
    ) -> dict[str, Any]:
        rev = Revision(
            project_id=project_id,
            revision_number=revision_number,
            model_sha256=model_sha256,
            model_storage_key=model_storage_key,
            author_user_id=author_user_id,
            reason=reason,
            rule_pack_version=rule_pack_version,
            parent_revision_id=parent_revision_id,
            command_id=command_id,
            idempotency_key=idempotency_key,
            command_fingerprint=command_fingerprint,
            engine_version=engine_version,
            validation_state=validation_state,
        )
        self._s.add(rev)
        self._s.flush()
        return _row(rev)

    def get(self, revision_id: uuid.UUID) -> dict[str, Any] | None:
        row = self._s.get(Revision, revision_id)
        return _row(row) if row else None

    def get_by_idempotency(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> dict[str, Any] | None:
        row = self._s.scalar(
            select(Revision).where(
                Revision.project_id == project_id,
                Revision.idempotency_key == idempotency_key,
            )
        )
        return _row(row) if row else None

    def list_for_project(self, project_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self._s.scalars(
            select(Revision).where(Revision.project_id == project_id)
        ).all()
        return [_row(r) for r in rows]

    def set_validation_report_sha256(self, revision_id: uuid.UUID, sha256: str) -> None:
        rev = self._s.get(Revision, revision_id)
        if rev:
            rev.validation_report_sha256 = sha256
            self._s.flush()


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
class SqlJobRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def enqueue(
        self,
        project_id: uuid.UUID,
        job_type: str,
        payload: dict[str, Any],
        created_by_user_id: uuid.UUID | None,
        revision_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        job = Job(
            project_id=project_id,
            type=job_type,
            payload=payload,
            status="queued",
            created_by_user_id=created_by_user_id,
            revision_id=revision_id,
        )
        self._s.add(job)
        self._s.flush()
        return _row(job)

    def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        progress: int | None = None,
        error: str | None = None,
    ) -> None:
        job = self._s.get(Job, job_id)
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if error is not None:
                job.error = error
            if status == "running" and not job.started_at:
                job.started_at = datetime.now(timezone.utc)
            if status in ("succeeded", "failed", "cancelled"):
                job.finished_at = datetime.now(timezone.utc)
            self._s.flush()

    def get(self, job_id: uuid.UUID) -> dict[str, Any] | None:
        row = self._s.get(Job, job_id)
        return _row(row) if row else None

    def list_for_project(self, project_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self._s.scalars(
            select(Job).where(Job.project_id == project_id)
        ).all()
        return [_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------
class SqlArtifactRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self,
        job_id: uuid.UUID,
        kind: str,
        storage_key: str,
        sha256: str,
        size_bytes: int | None = None,
    ) -> dict[str, Any]:
        art = Artifact(
            job_id=job_id, kind=kind,
            storage_key=storage_key, sha256=sha256,
            size_bytes=size_bytes,
        )
        self._s.add(art)
        self._s.flush()
        return _row(art)

    def list_for_job(self, job_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self._s.scalars(
            select(Artifact).where(Artifact.job_id == job_id)
        ).all()
        return [_row(r) for r in rows]

    def get_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        row = self._s.scalar(select(Artifact).where(Artifact.sha256 == sha256))
        return _row(row) if row else None


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
class SqlAuditRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def record(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        organization_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        evt = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            payload=payload or {},
            request_id=request_id,
        )
        self._s.add(evt)
        self._s.flush()

    def list_for_org(
        self,
        org_id: uuid.UUID,
        limit: int = 100,
        before_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        q = select(AuditEvent).where(AuditEvent.organization_id == org_id)
        rows = self._s.scalars(q.order_by(AuditEvent.created_at.desc()).limit(limit)).all()
        return [_row(r) for r in rows]
