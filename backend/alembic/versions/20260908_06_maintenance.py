"""Maintenance availability constraints."""
import sqlalchemy as sa

from alembic import op

revision = "20260908_06"
down_revision = "20260908_05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("trip_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(500), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_trip_events_trip_id", "trip_events", ["trip_id"])
    op.add_column("vehicles", sa.Column("odometer_km", sa.Integer(), server_default="0", nullable=False))
    op.add_column("vehicles", sa.Column("maintenance_due_km", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("maintenance_due_on", sa.Date(), nullable=True))


def downgrade():
    op.drop_table("trip_events")
    for field in ("maintenance_due_on", "maintenance_due_km", "odometer_km"):
        op.drop_column("vehicles", field)
