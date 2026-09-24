"""Durable metadata storage for the FastAPI adapter.

The geometry engine remains file-backed and authoritative.  This module stores
only project metadata, revision pointers, job state, artifact metadata, and
audit events.  SQLite is deliberately used for the local and test adapter so
the API can be run without a database service; ``schema.sql`` and the initial
migration provide the equivalent PostgreSQL contract for deployed environments.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


class DurableStore:
    """SQLite implementation of the E02 metadata repositories."""

    def __init__(self, root: Path, db_path: str | Path | None = None) -> None:
        configured_path = db_path or os.getenv("APP_DB_PATH")
        self.db_path = Path(configured_path or root / ".data" / "architectural-planning-platform.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()
        self.projects = ProjectRepository(self)
        self.revisions = RevisionRepository(self)
        self.jobs = JobRepository(self)
        self.artifacts = ArtifactRepository(self)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    external_auth_id TEXT UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS memberships (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL REFERENCES organizations(id),
                    user_id TEXT NOT NULL REFERENCES users(id),
                    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer', 'reviewer')),
                    created_at TEXT NOT NULL,
                    UNIQUE (organization_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL REFERENCES organizations(id),
                    name TEXT NOT NULL,
                    units TEXT NOT NULL DEFAULT 'inch',
                    current_revision_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS revisions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    revision_number INTEGER NOT NULL,
                    parent_revision_id TEXT REFERENCES revisions(id),
                    model_storage_key TEXT,
                    model_sha256 TEXT,
                    rule_pack_version TEXT,
                    author_user_id TEXT REFERENCES users(id),
                    reason TEXT,
                    validation_report_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE (project_id, revision_number)
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    revision_id TEXT REFERENCES revisions(id),
                    type TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
                    ),
                    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
                    payload TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_by_user_id TEXT REFERENCES users(id),
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id),
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT REFERENCES organizations(id),
                    actor_user_id TEXT REFERENCES users(id),
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    payload TEXT NOT NULL DEFAULT '{}',
                    request_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_projects_org
                    ON projects(organization_id);
                CREATE INDEX IF NOT EXISTS idx_revisions_project
                    ON revisions(project_id, revision_number);
                CREATE INDEX IF NOT EXISTS idx_jobs_status_created
                    ON jobs(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_artifacts_job
                    ON artifacts(job_id);
                CREATE INDEX IF NOT EXISTS idx_audit_org_created
                    ON audit_events(organization_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_memberships_user
                    ON memberships(user_id);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, utc_now()),
            )

    def health(self) -> dict[str, Any]:
        try:
            with self.connection() as connection:
                connection.execute("SELECT 1").fetchone()
            return {"status": "ok", "engine": "sqlite", "path": str(self.db_path)}
        except sqlite3.Error as exc:
            return {"status": "error", "engine": "sqlite", "error": str(exc)}

    def seed_banswara(self, model_path: Path) -> dict[str, Any]:
        """Seed the known project without copying or mutating its model files."""
        now = utc_now()
        organization_id = "org-banswara-bar-association"
        project_id = "proj-banswara-bar-association"
        model_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest() if model_path.exists() else None
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO organizations
                    (id, name, slug, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (organization_id, "Banswara Bar Association", "banswara-bar-association", now, now),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO projects
                    (id, organization_id, name, units, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, organization_id, "Bar Association Hall - Banswara", "inch", now, now),
            )
            revision = connection.execute(
                "SELECT id FROM revisions WHERE project_id = ? ORDER BY revision_number LIMIT 1",
                (project_id,),
            ).fetchone()
            if revision is None:
                revision_id = "rev-banswara-001"
                connection.execute(
                    """
                    INSERT INTO revisions
                        (id, project_id, revision_number, model_storage_key,
                         model_sha256, rule_pack_version, reason, created_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision_id,
                        project_id,
                        "bar-association-hall/standard/model/project.json",
                        model_sha256,
                        "india-preliminary-review.v1",
                        "E02 file-backed seed",
                        now,
                    ),
                )
            else:
                revision_id = str(revision["id"])
            connection.execute(
                "UPDATE projects SET current_revision_id = ?, updated_at = ? WHERE id = ?",
                (revision_id, now, project_id),
            )
        return self.projects.get(project_id) or {}

    def create_project(self, project_id: str, organization_id: str, name: str, units: str) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO projects
                    (id, organization_id, name, units, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, organization_id, name, units, now, now),
            )
        return self.projects.get(project_id) or {}

    def create_revision(
        self,
        project_id: str,
        *,
        model_storage_key: str | None = None,
        model_sha256: str | None = None,
        rule_pack_version: str | None = None,
        reason: str | None = None,
        parent_revision_id: str | None = None,
        author_user_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        revision_id = new_id("rev")
        with self.connection() as connection:
            latest = connection.execute(
                "SELECT COALESCE(MAX(revision_number), 0) AS number FROM revisions WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            revision_number = int(latest["number"]) + 1
            connection.execute(
                """
                INSERT INTO revisions
                    (id, project_id, revision_number, parent_revision_id,
                     model_storage_key, model_sha256, rule_pack_version,
                     author_user_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    project_id,
                    revision_number,
                    parent_revision_id,
                    model_storage_key,
                    model_sha256,
                    rule_pack_version,
                    author_user_id,
                    reason,
                    now,
                ),
            )
            connection.execute(
                "UPDATE projects SET current_revision_id = ?, updated_at = ? WHERE id = ?",
                (revision_id, now, project_id),
            )
        return self.revisions.get(revision_id) or {}

    def create_job(
        self,
        project_id: str,
        job_type: str,
        payload: dict[str, Any],
        revision_id: str | None = None,
        created_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        job_id = new_id("job")
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs
                    (id, project_id, revision_id, type, status, payload, created_by_user_id, created_at)
                VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (
                    job_id,
                    project_id,
                    revision_id,
                    job_type,
                    json.dumps(payload, sort_keys=True),
                    created_by_user_id,
                    utc_now(),
                ),
            )
        return self.jobs.get(job_id) or {}

    def complete_generation(self, job_id: str) -> dict[str, Any]:
        """Advance one queued generation job and create durable artifact metadata."""
        result: dict[str, Any] = {}
        with self.connection() as connection:
            job = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                return {}
            if job["status"] not in {"queued", "running"}:
                result = dict(job)
                result["payload"] = json.loads(result["payload"])
                result["artifactIds"] = [
                    str(item["id"])
                    for item in connection.execute(
                        "SELECT id FROM artifacts WHERE job_id = ? ORDER BY created_at, id", (job_id,)
                    ).fetchall()
                ]
                return result
            now = utc_now()
            connection.execute(
                """
                UPDATE jobs SET status = 'running', progress = 50, started_at = COALESCE(started_at, ?)
                WHERE id = ?
                """,
                (now, job_id),
            )
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM artifacts WHERE job_id = ?", (job_id,)
            ).fetchone()
            if int(existing["count"]) == 0:
                kinds = ("dxf-gf", "dxf-ff", "pdf-gf", "pdf-ff", "review-pdf")
                for kind in kinds:
                    artifact_id = new_id("art")
                    extension = "dxf" if kind.startswith("dxf") else "pdf"
                    name = f"{job_id}-{kind.replace('-', '_')}.{extension}"
                    digest = hashlib.sha256(f"{job_id}:{kind}".encode()).hexdigest()
                    connection.execute(
                        """
                        INSERT INTO artifacts
                            (id, job_id, kind, name, storage_key, sha256, size_bytes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            artifact_id,
                            job_id,
                            kind,
                            name,
                            f"artifacts/{digest[:2]}/{digest}.{extension}",
                            digest,
                            0,
                            now,
                        ),
                    )
            connection.execute(
                """
                UPDATE jobs SET status = 'succeeded', progress = 100, finished_at = ?
                WHERE id = ?
                """,
                (utc_now(), job_id),
            )
        return self.jobs.get(job_id) or {}


class ProjectRepository:
    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def get(self, project_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            row = connection.execute(
                """
                SELECT p.*, r.revision_number AS current_revision_number
                FROM projects p
                LEFT JOIN revisions r ON r.id = p.current_revision_id
                WHERE p.id = ? AND p.deleted_at IS NULL
                """,
                (project_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_for_organization(self, organization_id: str) -> list[dict[str, Any]]:
        with self.store.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM projects WHERE organization_id = ? AND deleted_at IS NULL ORDER BY name",
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]


class RevisionRepository:
    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def get(self, revision_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            row = connection.execute("SELECT * FROM revisions WHERE id = ?", (revision_id,)).fetchone()
        return dict(row) if row else None

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        with self.store.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM revisions WHERE project_id = ? ORDER BY revision_number",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]


class JobRepository:
    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["payload"] = json.loads(result["payload"])
            result["artifactIds"] = [
                str(item["id"])
                for item in connection.execute(
                    "SELECT id FROM artifacts WHERE job_id = ? ORDER BY created_at, id", (job_id,)
                ).fetchall()
            ]
            return result


class ArtifactRepository:
    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        return dict(row) if row else None

    def list_for_job(self, job_id: str) -> list[dict[str, Any]]:
        with self.store.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at, id", (job_id,)
            ).fetchall()
        return [dict(row) for row in rows]
