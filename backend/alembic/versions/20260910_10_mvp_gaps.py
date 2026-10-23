"""Complete load history and freight calculation foundations."""

import sqlalchemy as sa

from alembic import op

revision = "20260910_10"
down_revision = "20260909_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("freight_rule_versions", sa.Column("valid_from", sa.Date(), nullable=True))
    op.add_column("freight_rule_versions", sa.Column("valid_until", sa.Date(), nullable=True))
    op.create_index("ix_freight_rule_versions_valid_from", "freight_rule_versions", ["valid_from"])
    op.create_table(
        "load_versions",
        sa.Column("load_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("load_id", "version"),
    )
    op.create_index("ix_load_versions_load_id", "load_versions", ["load_id"])
    op.create_table(
        "freight_calculations",
        sa.Column("load_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("input_snapshot", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["freight_rule_versions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_freight_calculations_load_id", "freight_calculations", ["load_id"])


def downgrade() -> None:
    op.drop_index("ix_freight_calculations_load_id", table_name="freight_calculations")
    op.drop_table("freight_calculations")
    op.drop_index("ix_load_versions_load_id", table_name="load_versions")
    op.drop_table("load_versions")
    op.drop_index("ix_freight_rule_versions_valid_from", table_name="freight_rule_versions")
    op.drop_column("freight_rule_versions", "valid_until")
    op.drop_column("freight_rule_versions", "valid_from")
