"""Invalidate old sessions after password changes."""

import sqlalchemy as sa

from alembic import op

revision = "20260909_09"
down_revision = "20260909_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "session_version")
