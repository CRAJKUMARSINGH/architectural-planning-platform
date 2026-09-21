"""Add persistent command/idempotency metadata for revision transactions."""

from alembic import op
import sqlalchemy as sa


revision = "0002_revision_transaction_metadata"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("revisions", sa.Column("command_id", sa.String(120), nullable=True))
    op.add_column("revisions", sa.Column("idempotency_key", sa.String(200), nullable=True))
    op.add_column("revisions", sa.Column("command_fingerprint", sa.String(64), nullable=True))
    op.add_column(
        "revisions",
        sa.Column(
            "engine_version",
            sa.String(120),
            nullable=False,
            server_default="phase2.command-engine.v1",
        ),
    )
    op.add_column(
        "revisions",
        sa.Column("validation_state", sa.String(30), nullable=False, server_default="DRAFT"),
    )
    op.create_unique_constraint(
        "uq_revisions_project_idempotency", "revisions", ["project_id", "idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_revisions_project_idempotency", "revisions", type_="unique")
    op.drop_column("revisions", "validation_state")
    op.drop_column("revisions", "engine_version")
    op.drop_column("revisions", "command_fingerprint")
    op.drop_column("revisions", "idempotency_key")
    op.drop_column("revisions", "command_id")