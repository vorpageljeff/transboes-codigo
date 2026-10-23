"""Operational loads and trips.

Revision ID: 20260908_02
Revises: 20260907_01
"""

import sqlalchemy as sa

from alembic import op

revision = "20260908_02"
down_revision = "20260907_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    load_status = sa.Enum(
        "PENDENTE", "PROGRAMADA", "EM_TRANSITO", "ENTREGUE", "CANCELADA", name="loadstatus"
    )
    trip_status = sa.Enum(
        "PLANEJADA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA", name="tripstatus"
    )
    op.create_table(
        "loads",
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("customer", sa.String(160), nullable=False),
        sa.Column("product", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(160), nullable=False),
        sa.Column("destination", sa.String(160), nullable=False),
        sa.Column("weight_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("freight_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("pickup_date", sa.Date(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", load_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_loads_reference", "loads", ["reference"])
    op.create_index("ix_loads_customer", "loads", ["customer"])
    op.create_table(
        "trips",
        sa.Column("load_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", trip_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_load_id", "trips", ["load_id"])
    op.create_index("ix_trips_vehicle_id", "trips", ["vehicle_id"])
    op.create_index("ix_trips_driver_id", "trips", ["driver_id"])


def downgrade() -> None:
    op.drop_table("trips")
    op.drop_table("loads")
    sa.Enum(name="tripstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="loadstatus").drop(op.get_bind(), checkfirst=True)
