"""Track disabled user state for authorization checks."""

from alembic import op
import sqlalchemy as sa


revision = "0003_user_disabled_at"
down_revision = "0002_revision_transaction_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "disabled_at")