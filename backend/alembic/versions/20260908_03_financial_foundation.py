"""Financial, freight validation and audit foundation."""

import sqlalchemy as sa

from alembic import op

revision = "20260908_03"
down_revision = "20260908_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'FINANCIAL'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VIEWER'")
    validation_status = sa.Enum(
        "PENDENTE",
        "CONFERIDO_OK",
        "DIVERGENTE",
        "AJUSTADO_MANUALMENTE",
        "AGUARDANDO_REGRA",
        "NAO_APLICAVEL",
        name="freightvalidationstatus",
    )
    cost_category = sa.Enum(
        "COMBUSTIVEL", "PEDAGIO", "MANUTENCAO", "OUTRO", name="costcategory"
    )
    op.create_table(
        "freight_rule_sets",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_identity_columns(),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "freight_rule_versions",
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("configuration", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["rule_set_id"], ["freight_rule_sets.id"]),
    )
    op.create_index("ix_freight_rule_versions_rule_set_id", "freight_rule_versions", ["rule_set_id"])
    op.create_table(
        "freight_validations",
        sa.Column("load_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("received_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("difference", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", validation_status, nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["freight_rule_versions.id"]),
    )
    op.create_index("ix_freight_validations_load_id", "freight_validations", ["load_id"])
    op.create_table(
        "freight_manual_adjustments",
        sa.Column("validation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("previous_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("adjusted_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["validation_id"], ["freight_validations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_freight_manual_adjustments_validation_id", "freight_manual_adjustments", ["validation_id"])
    op.create_table(
        "revenue_entries",
        sa.Column("load_id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("recognized_on", sa.Date(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.UniqueConstraint("load_id"),
    )
    op.create_index("ix_revenue_entries_load_id", "revenue_entries", ["load_id"])
    op.create_index("ix_revenue_entries_recognized_on", "revenue_entries", ["recognized_on"])
    op.create_table(
        "trip_costs",
        sa.Column("trip_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("category", cost_category, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("incurred_on", sa.Date(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
    )
    op.create_index("ix_trip_costs_trip_id", "trip_costs", ["trip_id"])
    op.create_index("ix_trip_costs_vehicle_id", "trip_costs", ["vehicle_id"])
    op.create_index("ix_trip_costs_incurred_on", "trip_costs", ["incurred_on"])
    op.create_table(
        "audit_logs",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80), nullable=True),
        sa.Column("decision_source", sa.String(40), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def _identity_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("trip_costs")
    op.drop_table("revenue_entries")
    op.drop_table("freight_manual_adjustments")
    op.drop_table("freight_validations")
    op.drop_table("freight_rule_versions")
    op.drop_table("freight_rule_sets")
    sa.Enum(name="costcategory").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="freightvalidationstatus").drop(op.get_bind(), checkfirst=True)
