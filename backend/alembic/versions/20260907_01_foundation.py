"""Foundation models."""

import sqlalchemy as sa

from alembic import op

revision = "20260907_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("ADMIN", "MANAGER", "OPERATOR", name="userrole")
    vehicle_status = sa.Enum(
        "DISPONIVEL",
        "RESERVADO",
        "EM_ROTA",
        "DESCARGA",
        "RETORNO_BASE",
        "MANUTENCAO",
        "INATIVO",
        name="vehiclestatus",
    )
    op.create_table(
        "users",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "vehicles",
        sa.Column("plate", sa.String(10), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("capacity_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", vehicle_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plate"),
    )
    op.create_index("ix_vehicles_plate", "vehicles", ["plate"])
    op.create_table(
        "drivers",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("license_number", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_number"),
    )
    op.create_index("ix_drivers_name", "drivers", ["name"])
    op.create_table(
        "locations",
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("source", sa.String(80)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_name", "locations", ["name"])


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_table("drivers")
    op.drop_table("vehicles")
    op.drop_table("users")
    sa.Enum(name="vehiclestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
