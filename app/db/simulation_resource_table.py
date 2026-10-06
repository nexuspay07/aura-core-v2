"""Canonical Simulation resources and immutable runs."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    UniqueConstraint,
    func,
)

from app.db.database import metadata


simulation_resource_table = Table(
    "simulation_resources",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(36), nullable=False),
    Column("title", String(255), nullable=False),
    Column("simulation_type", String(64), nullable=False),
    Column("created_by_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("owner_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
    Column("source_strategy_id", Integer, ForeignKey("strategy_resources.id", ondelete="RESTRICT"), nullable=False),
    Column("source_strategy_revision_id", Integer, ForeignKey("strategy_revisions.id", ondelete="RESTRICT"), nullable=False),
    Column("source_decision_snapshot_id", Integer, ForeignKey("decision_execution_snapshots.id", ondelete="RESTRICT"), nullable=True),
    Column("current_run_number", Integer, nullable=False, default=0, server_default="0"),
    Column("lock_version", Integer, nullable=False, default=1, server_default="1"),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    UniqueConstraint("public_id", name="uq_simulation_resources_public_id"),
    CheckConstraint("length(trim(title)) > 0", name="ck_simulation_resources_title_nonempty"),
    CheckConstraint("simulation_type = 'strategy_stress_test'", name="ck_simulation_resources_type"),
    CheckConstraint("current_run_number >= 0", name="ck_simulation_resources_current_run_nonnegative"),
    CheckConstraint("lock_version > 0", name="ck_simulation_resources_lock_version_positive"),
    CheckConstraint(
        "(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR "
        "(owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)",
        name="ck_simulation_resources_tenancy_shape",
    ),
)

Index(
    "ix_simulation_resources_owner_archive_updated",
    simulation_resource_table.c.owner_user_id,
    simulation_resource_table.c.archived_at,
    simulation_resource_table.c.updated_at,
)
Index(
    "ix_simulation_resources_workspace_archive_updated",
    simulation_resource_table.c.organization_id,
    simulation_resource_table.c.workspace_id,
    simulation_resource_table.c.archived_at,
    simulation_resource_table.c.updated_at,
)
Index("ix_simulation_resources_strategy_revision", simulation_resource_table.c.source_strategy_id, simulation_resource_table.c.source_strategy_revision_id)
Index("ix_simulation_resources_decision_snapshot", simulation_resource_table.c.source_decision_snapshot_id)


simulation_run_table = Table(
    "simulation_runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("simulation_resource_id", Integer, ForeignKey("simulation_resources.id", ondelete="CASCADE"), nullable=False),
    Column("run_number", Integer, nullable=False),
    Column("canonical_execution_input_json", JSON, nullable=False),
    Column("canonical_result_json", JSON, nullable=False),
    Column("input_schema_version", Integer, nullable=False),
    Column("result_schema_version", Integer, nullable=False),
    Column("engine_version", String(64), nullable=False),
    Column("provider_name", String(128), nullable=True),
    Column("model_name", String(255), nullable=True),
    Column("determinism_mode", String(32), nullable=False),
    Column("created_by_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("simulation_resource_id", "run_number", name="uq_simulation_runs_resource_run"),
    CheckConstraint("run_number > 0", name="ck_simulation_runs_run_positive"),
    CheckConstraint("input_schema_version > 0", name="ck_simulation_runs_input_schema_positive"),
    CheckConstraint("result_schema_version > 0", name="ck_simulation_runs_result_schema_positive"),
    CheckConstraint("length(trim(engine_version)) > 0", name="ck_simulation_runs_engine_nonempty"),
    CheckConstraint("determinism_mode IN ('model_assisted')", name="ck_simulation_runs_determinism_mode"),
)

Index("ix_simulation_runs_resource_created", simulation_run_table.c.simulation_resource_id, simulation_run_table.c.created_at)
