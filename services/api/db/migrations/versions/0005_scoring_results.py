"""Add AI scoring results table for Phase 16A version scoring integration."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_scoring_results"
down_revision = "0004_collaboration_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scoring_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revisions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("brief_analysis_id", sa.String(255), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("program_fit", sa.Integer(), nullable=False),
        sa.Column("daylight_score", sa.Integer(), nullable=False),
        sa.Column("budget_fit", sa.Integer(), nullable=False),
        sa.Column("commentary", sa.Text(), nullable=False),
        sa.Column("zone_scores", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("provenance", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="gemini-2.5-flash"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="ck_scoring_overall_score"),
        sa.CheckConstraint("program_fit >= 0 AND program_fit <= 100", name="ck_scoring_program_fit"),
        sa.CheckConstraint("daylight_score >= 0 AND daylight_score <= 100", name="ck_scoring_daylight_score"),
        sa.CheckConstraint("budget_fit >= 0 AND budget_fit <= 100", name="ck_scoring_budget_fit"),
    )
    op.create_index("idx_scoring_results_project", "scoring_results", ["project_id"])
    op.create_index("idx_scoring_results_revision", "scoring_results", ["revision_id"], unique=True)
    op.create_index("idx_scoring_results_created", "scoring_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_scoring_results_created", table_name="scoring_results")
    op.drop_index("idx_scoring_results_revision", table_name="scoring_results")
    op.drop_index("idx_scoring_results_project", table_name="scoring_results")
    op.drop_table("scoring_results")