"""add canonical Simulation persistence foundation"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0027"
down_revision = "20260924_0026"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "simulation_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("simulation_type", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_strategy_id", sa.Integer(), sa.ForeignKey("strategy_resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_strategy_revision_id", sa.Integer(), sa.ForeignKey("strategy_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_decision_snapshot_id", sa.Integer(), sa.ForeignKey("decision_execution_snapshots.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("current_run_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_simulation_resources_public_id"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_simulation_resources_title_nonempty"),
        sa.CheckConstraint("simulation_type = 'strategy_stress_test'", name="ck_simulation_resources_type"),
        sa.CheckConstraint("current_run_number >= 0", name="ck_simulation_resources_current_run_nonnegative"),
        sa.CheckConstraint("lock_version > 0", name="ck_simulation_resources_lock_version_positive"),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR "
            "(owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)",
            name="ck_simulation_resources_tenancy_shape",
        ),
    )
    op.create_index("ix_simulation_resources_owner_archive_updated", "simulation_resources", ["owner_user_id", "archived_at", "updated_at"])
    op.create_index("ix_simulation_resources_workspace_archive_updated", "simulation_resources", ["organization_id", "workspace_id", "archived_at", "updated_at"])
    op.create_index("ix_simulation_resources_strategy_revision", "simulation_resources", ["source_strategy_id", "source_strategy_revision_id"])
    op.create_index("ix_simulation_resources_decision_snapshot", "simulation_resources", ["source_decision_snapshot_id"])

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("simulation_resource_id", sa.Integer(), sa.ForeignKey("simulation_resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("canonical_execution_input_json", sa.JSON(), nullable=False),
        sa.Column("canonical_result_json", sa.JSON(), nullable=False),
        sa.Column("input_schema_version", sa.Integer(), nullable=False),
        sa.Column("result_schema_version", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(255), nullable=True),
        sa.Column("determinism_mode", sa.String(32), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("simulation_resource_id", "run_number", name="uq_simulation_runs_resource_run"),
        sa.CheckConstraint("run_number > 0", name="ck_simulation_runs_run_positive"),
        sa.CheckConstraint("input_schema_version > 0", name="ck_simulation_runs_input_schema_positive"),
        sa.CheckConstraint("result_schema_version > 0", name="ck_simulation_runs_result_schema_positive"),
        sa.CheckConstraint("length(trim(engine_version)) > 0", name="ck_simulation_runs_engine_nonempty"),
        sa.CheckConstraint("determinism_mode IN ('model_assisted')", name="ck_simulation_runs_determinism_mode"),
    )
    op.create_index("ix_simulation_runs_resource_created", "simulation_runs", ["simulation_resource_id", "created_at"])


def downgrade():
    op.drop_table("simulation_runs")
    op.drop_table("simulation_resources")
