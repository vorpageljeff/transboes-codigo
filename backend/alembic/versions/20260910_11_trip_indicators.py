"""Operational indicators on trip events."""

import sqlalchemy as sa

from alembic import op

revision = "20260910_11"
down_revision = "20260910_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trip_events", sa.Column("odometer_km", sa.Integer(), nullable=True))
    op.add_column("trip_events", sa.Column("distance_km", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("trip_events", "distance_km")
    op.drop_column("trip_events", "odometer_km")
