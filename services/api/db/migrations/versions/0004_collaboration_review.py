"""Add immutable review links, anchored comments, and approval events."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_collaboration_review"
down_revision = "0003_user_disabled_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("view", sa.String(20), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("view IN ('technical','presentation')", name="ck_review_link_view"),
    )
    op.create_index("idx_review_links_project", "review_links", ["project_id", "created_at"])
    op.create_index("idx_review_links_token_hash", "review_links", ["token_hash"], unique=True)

    op.create_table(
        "review_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("anchor_type", sa.String(30), nullable=False),
        sa.Column("anchor_id", sa.String(200), nullable=False),
        sa.Column("viewpoint", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "anchor_type IN ('room','space','wall','opening','dimension','validation-finding','render-viewpoint')",
            name="ck_review_comment_anchor_type",
        ),
    )
    op.create_index("idx_review_comments_project_revision", "review_comments", ["project_id", "revision_id", "created_at"])

    op.create_table(
        "review_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "state IN ('Draft','Review','Client Presentation','Preliminary Coordination','Not Issuable')",
            name="ck_review_approval_state",
        ),
    )
    op.create_index("idx_review_approvals_project_created", "review_approvals", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_review_approvals_project_created", table_name="review_approvals")
    op.drop_table("review_approvals")
    op.drop_index("idx_review_comments_project_revision", table_name="review_comments")
    op.drop_table("review_comments")
    op.drop_index("idx_review_links_token_hash", table_name="review_links")
    op.drop_index("idx_review_links_project", table_name="review_links")
    op.drop_table("review_links")