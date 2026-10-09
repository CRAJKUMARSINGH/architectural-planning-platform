"""Workflow ORM models — Archi Copilot integration.

These three tables bring the client-brief → canvas → score → suggest workflow
into the Platform's database.  They hang off the existing Project (UUID PK)
and share the Platform's auth and org-isolation model.

Geometry authority remains in the Python engine (traecad_engine).
Canvas blocks stored here are *concept-level sketches only* — they become
authoritative geometry only after an explicit 'Promote to Model' action
that queues a generate Job.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .orm import Project  # noqa: F401 — imported so relationships resolve

JSONB = JSON().with_variant(PG_JSONB(), "postgresql")


# ---------------------------------------------------------------------------
# BriefAnalysis
# ---------------------------------------------------------------------------
class BriefAnalysis(Base):
    """AI-structured analysis of a client brief.

    One project can have many analyses (re-run any time the brief changes).
    The *latest* record is considered current.  Earlier records are kept for
    audit/comparison.

    Mirrors Archi Copilot's ``brief_analyses`` table but uses UUID PKs and
    links to the Platform's Project.
    """

    __tablename__ = "brief_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Raw brief text captured at analysis time so the result is self-contained.
    brief_text: Mapped[str] = mapped_column(Text, nullable=False)

    # AI-produced fields (all stored as JSONB for flexibility).
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"name": str, "sqm": float, "priority": "must_have"|"nice_to_have", "notes": str|None}]
    space_program: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    constraints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    opportunities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    open_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Provenance — model version, timestamp, etc. from AIService.
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(
        String(80), nullable=False, default="gemini-2.5-flash"
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


# ---------------------------------------------------------------------------
# ConceptVersion  (canvas snapshot)
# ---------------------------------------------------------------------------
class ConceptVersion(Base):
    """A named snapshot of the concept canvas for a project.

    Each version stores:
    - An ordered list of floor names (e.g. ["Ground Floor", "First Floor"])
    - The canvas blocks for all floors as JSONB
    - Optional AI scores once the architect requests scoring

    Canvas blocks structure (mirrors Archi Copilot CanvasBlock):
    [
      {
        "id": "uuid-string",
        "label": "Living Room",
        "zoneType": "living",   # living | sleeping | service | circulation | outdoor | work | other
        "floor": "Ground Floor",
        "x": 100, "y": 80, "width": 200, "height": 150
      }
    ]

    IMPORTANT: these are concept-level sketches. They must NOT be treated as
    authoritative geometry. Promote to a geometry revision via a queued Job.
    """

    __tablename__ = "concept_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brief_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("brief_analyses.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordered list of floor names: ["Ground Floor", "First Floor"]
    floors: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: ["Ground Floor"])
    # All canvas blocks across all floors
    blocks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # AI scores — null until the architect requests scoring.
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    program_fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    daylight_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_commentary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to geometry revision if this concept was promoted.
    promoted_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


# ---------------------------------------------------------------------------
# CopilotSuggestion
# ---------------------------------------------------------------------------
VALID_SUGGESTION_CATEGORIES = (
    "program", "site", "daylight", "budget", "circulation", "general"
)
VALID_SUGGESTION_STATUSES = ("new", "accepted", "dismissed")


class CopilotSuggestion(Base):
    """Proactive AI suggestion for a project.

    Suggestions are generated on demand and can be accepted or dismissed.
    Accepted suggestions should be actioned in the brief or canvas;
    dismissed suggestions are kept for audit purposes.
    """

    __tablename__ = "copilot_suggestions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('program','site','daylight','budget','circulation','general')",
            name="ck_copilot_suggestion_category",
        ),
        CheckConstraint(
            "status IN ('new','accepted','dismissed')",
            name="ck_copilot_suggestion_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")

    # SHA-256 hash of (category + text) for deduplication.
    suggestion_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(
        String(80), nullable=False, default="gemini-2.5-flash"
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
