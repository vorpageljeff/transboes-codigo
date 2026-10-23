"""Versioned Copagril imports and historical load fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260908_04"
down_revision = "20260908_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_status = sa.Enum(
        "PROCESSANDO",
        "CONCLUIDA",
        "CONCLUIDA_COM_ERROS",
        "FALHOU",
        "DUPLICADA",
        name="importrunstatus",
    )
    op.add_column("loads", sa.Column("external_id", sa.String(80), nullable=True))
    op.add_column("loads", sa.Column("expected_freight_value", sa.Numeric(12, 2), nullable=True))
    op.add_column("loads", sa.Column("distance_km", sa.Numeric(10, 2), nullable=True))
    op.add_column("loads", sa.Column("quantity", sa.Integer(), nullable=True))
    op.add_column("loads", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("loads", sa.Column("facility_code", sa.String(20), nullable=True))
    op.add_column("loads", sa.Column("source", sa.String(40), server_default="MANUAL", nullable=False))
    op.create_index("ix_loads_external_id", "loads", ["external_id"], unique=True)
    op.create_table(
        "import_profiles",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_identity(),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "import_profile_versions",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("field_mapping", sa.Text(), nullable=False),
        sa.Column("validation_rules", sa.Text(), nullable=False),
        sa.Column("cancellation_rules", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_identity(),
        sa.ForeignKeyConstraint(["profile_id"], ["import_profiles.id"]),
        sa.UniqueConstraint("profile_id", "version"),
    )
    op.create_index("ix_import_profile_versions_profile_id", "import_profile_versions", ["profile_id"])
    op.create_table(
        "import_runs",
        sa.Column("profile_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source_checksum", sa.String(64), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("imported_rows", sa.Integer(), nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        *_identity(),
        sa.ForeignKeyConstraint(["profile_version_id"], ["import_profile_versions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_import_runs_source_checksum", "import_runs", ["source_checksum"], unique=True)
    op.create_table(
        "import_rows",
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(80), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=False),
        sa.Column("errors", sa.Text(), nullable=False),
        sa.Column("style_markers", sa.Text(), nullable=False),
        *_identity(),
        sa.ForeignKeyConstraint(["import_run_id"], ["import_runs.id"]),
        sa.UniqueConstraint("import_run_id", "row_number"),
    )
    op.create_index("ix_import_rows_import_run_id", "import_rows", ["import_run_id"])
    op.create_index("ix_import_rows_external_id", "import_rows", ["external_id"])


def _identity() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("import_runs")
    op.drop_table("import_profile_versions")
    op.drop_table("import_profiles")
    op.drop_index("ix_loads_external_id", table_name="loads")
    for column in (
        "source",
        "facility_code",
        "received_at",
        "quantity",
        "distance_km",
        "expected_freight_value",
        "external_id",
    ):
        op.drop_column("loads", column)
    sa.Enum(name="importrunstatus").drop(op.get_bind(), checkfirst=True)
