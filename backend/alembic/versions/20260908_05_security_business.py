"""Collection workflow and exclusive active reservations."""

import sqlalchemy as sa

from alembic import op

revision = "20260908_05"
down_revision = "20260908_04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("revoked_sessions", sa.Column("token_hash", sa.String(64), primary_key=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_revoked_sessions_expires_at", "revoked_sessions", ["expires_at"])
    op.create_table(
        "collection_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("load_id", sa.Uuid(), sa.ForeignKey("loads.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("claim_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(500), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("receipt_reference", sa.String(500), nullable=True),
    )
    for field in ("load_id", "vehicle_id", "driver_id"):
        op.create_index(
            "uq_active_trip_" + field,
            "trips",
            [field],
            unique=True,
            postgresql_where=sa.text("status IN ('PLANEJADA', 'EM_ANDAMENTO')"),
            sqlite_where=sa.text("status IN ('PLANEJADA', 'EM_ANDAMENTO')"),
        )


def downgrade():
    for field in ("load_id", "vehicle_id", "driver_id"):
        op.drop_index("uq_active_trip_" + field, table_name="trips")
    op.drop_table("collection_cases")
    op.drop_table("revoked_sessions")
