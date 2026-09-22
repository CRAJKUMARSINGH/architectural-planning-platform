"""SQLAlchemy ORM models — E02 Persistence.

Geometry authority remains in Python workers; only metadata / pointers live here.
See docs/architecture/ADR-001-Geometry-Authority.md
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

JSONB = JSON().with_variant(PG_JSONB(), "postgresql")
# Alias used by Phase 11 collaboration columns — SQLite-safe JSON
JSON_TYPE = JSONB
UUID = Uuid




from .base import Base, TimestampMixin

# Keep the Postgres JSONB contract while allowing the documented SQLite
# development fallback to create and exercise the same ORM schema.
# JSONB (defined above) is the SQLite-compatible JSON column type.
JSON_TYPE = JSONB

# ---------------------------------------------------------------------------
# Organization  (ADR-003 primary isolation boundary)
# ---------------------------------------------------------------------------
class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_auth_id: Mapped[str | None] = mapped_column(Text, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    disabled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------
VALID_ROLES = ("owner", "editor", "viewer", "reviewer")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint("role IN ('owner','editor','viewer','reviewer')", name="ck_membership_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    units: Mapped[str] = mapped_column(String(10), nullable=False, default="inch")
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    revisions: Mapped[list["Revision"]] = relationship(
        back_populates="project", foreign_keys="Revision.project_id"
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="project")


# ---------------------------------------------------------------------------
# Revision  (geometry pointer — ADR-001)
# ---------------------------------------------------------------------------
class Revision(Base):
    __tablename__ = "revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "revision_number"),
        UniqueConstraint("project_id", "idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id"), nullable=True
    )
    # Object-store pointer — NEVER inline geometry (ADR-001)
    model_storage_key: Mapped[str | None] = mapped_column(Text)
    model_sha256: Mapped[str | None] = mapped_column(String(64))
    rule_pack_version: Mapped[str | None] = mapped_column(Text)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    validation_report_sha256: Mapped[str | None] = mapped_column(String(64))
    command_id: Mapped[str | None] = mapped_column(String(120))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    command_fingerprint: Mapped[str | None] = mapped_column(String(64))
    engine_version: Mapped[str] = mapped_column(
        String(120), nullable=False, default="phase2.command-engine.v1"
    )
    validation_state: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DRAFT"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    project: Mapped["Project"] = relationship(
        back_populates="revisions", foreign_keys=[project_id]
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="revision")


# ---------------------------------------------------------------------------
# Collaboration and review (Phase 11 — append-only review records)
# ---------------------------------------------------------------------------
VALID_REVIEW_VIEWS = ("technical", "presentation")
VALID_REVIEW_ANCHORS = (
    "room",
    "space",
    "wall",
    "opening",
    "dimension",
    "validation-finding",
    "render-viewpoint",
)
VALID_APPROVAL_STATES = (
    "Draft",
    "Review",
    "Client Presentation",
    "Preliminary Coordination",
    "Not Issuable",
)


class ReviewLink(Base):
    """Immutable bearer link pinned to one project revision."""

    __tablename__ = "review_links"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        CheckConstraint("view IN ('technical','presentation')", name="ck_review_link_view"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    view: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ReviewComment(Base):
    """Append-only comment anchored to a pinned revision."""

    __tablename__ = "review_comments"
    __table_args__ = (
        CheckConstraint(
            "anchor_type IN ('room','space','wall','opening','dimension',"
            "'validation-finding','render-viewpoint')",
            name="ck_review_comment_anchor_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    anchor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    anchor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    viewpoint: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ReviewApproval(Base):
    """Immutable approval-state event; current state is the latest event."""

    __tablename__ = "review_approvals"
    __table_args__ = (
        CheckConstraint(
            "state IN ('Draft','Review','Client Presentation',"
            "'Preliminary Coordination','Not Issuable')",
            name="ck_review_approval_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
VALID_JOB_TYPES = ("generate", "validate", "enrich", "quality_gate", "export", "benchmark")
VALID_JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "type IN ('generate','validate','enrich','quality_gate','export','benchmark')",
            name="ck_job_type",
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_job_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_job_progress"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("revisions.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")
    revision: Mapped["Revision | None"] = relationship(back_populates="jobs")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="job")


# ---------------------------------------------------------------------------
# Artifact  (content-addressed)
# ---------------------------------------------------------------------------
VALID_ARTIFACT_KINDS = (
    "dxf", "pdf", "svg", "json-report",
    "sbom", "performance-report", "adversarial-report",
)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    job: Mapped["Job"] = relationship(back_populates="artifacts")


# ---------------------------------------------------------------------------
# AuditEvent  (immutable — never UPDATE or DELETE)
# ---------------------------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    request_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
