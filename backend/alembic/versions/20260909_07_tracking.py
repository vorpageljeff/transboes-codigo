"""Vehicle position history for mobile and GPS providers."""

import sqlalchemy as sa

from alembic import op

revision = "20260909_07"
down_revision = "20260908_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_positions",
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(9, 2), nullable=True),
        sa.Column("speed_kmh", sa.Numeric(8, 2), nullable=True),
        sa.Column("heading", sa.Numeric(6, 2), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_positions_vehicle_id", "vehicle_positions", ["vehicle_id"])
    op.create_index(
        "ix_vehicle_positions_vehicle_captured",
        "vehicle_positions",
        ["vehicle_id", "captured_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_vehicle_positions_vehicle_captured", table_name="vehicle_positions")
    op.drop_index("ix_vehicle_positions_vehicle_id", table_name="vehicle_positions")
    op.drop_table("vehicle_positions")
