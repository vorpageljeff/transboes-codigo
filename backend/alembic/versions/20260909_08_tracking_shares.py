"""Temporary public links for trip location sharing."""

import sqlalchemy as sa

from alembic import op

revision = "20260909_08"
down_revision = "20260909_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracking_shares",
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tracking_shares_trip_id", "tracking_shares", ["trip_id"])
    op.create_index("ix_tracking_shares_created_by_id", "tracking_shares", ["created_by_id"])
    op.create_index("ix_tracking_shares_token_hash", "tracking_shares", ["token_hash"], unique=True)
    op.create_index("ix_tracking_shares_expires_at", "tracking_shares", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_tracking_shares_expires_at", table_name="tracking_shares")
    op.drop_index("ix_tracking_shares_token_hash", table_name="tracking_shares")
    op.drop_index("ix_tracking_shares_created_by_id", table_name="tracking_shares")
    op.drop_index("ix_tracking_shares_trip_id", table_name="tracking_shares")
    op.drop_table("tracking_shares")
