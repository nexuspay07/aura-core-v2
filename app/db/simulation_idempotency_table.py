"""Durable coordination records for canonical Simulation creation."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Table, func

from app.db.database import metadata


simulation_create_idempotency_table = Table(
    "simulation_create_idempotency",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("idempotency_key", String(255), nullable=False),
    Column("operation", String(64), nullable=False),
    Column("request_fingerprint", String(64), nullable=False),
    Column("actor_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("owner_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
    Column("status", String(20), nullable=False),
    Column("claim_token", String(36), nullable=True),
    Column("lease_expires_at", DateTime(timezone=True), nullable=True),
    Column("simulation_resource_id", Integer, ForeignKey("simulation_resources.id", ondelete="RESTRICT"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    CheckConstraint("length(trim(idempotency_key)) > 0", name="ck_simulation_create_idempotency_key_nonempty"),
    CheckConstraint("length(request_fingerprint) = 64", name="ck_simulation_create_idempotency_fingerprint"),
    CheckConstraint("operation = 'simulation_create_strategy_stress_test'", name="ck_simulation_create_idempotency_operation"),
    CheckConstraint("status IN ('in_progress', 'completed')", name="ck_simulation_create_idempotency_status"),
    CheckConstraint(
        "(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR "
        "(owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)",
        name="ck_simulation_create_idempotency_tenancy_shape",
    ),
    CheckConstraint(
        "(status = 'in_progress' AND simulation_resource_id IS NULL AND claim_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
        "(status = 'completed' AND simulation_resource_id IS NOT NULL AND claim_token IS NULL AND lease_expires_at IS NULL)",
        name="ck_simulation_create_idempotency_state",
    ),
)

Index(
    "uq_simulation_create_idempotency_personal_key",
    simulation_create_idempotency_table.c.actor_user_id,
    simulation_create_idempotency_table.c.owner_user_id,
    simulation_create_idempotency_table.c.operation,
    simulation_create_idempotency_table.c.idempotency_key,
    unique=True,
    sqlite_where=simulation_create_idempotency_table.c.owner_user_id.is_not(None),
    postgresql_where=simulation_create_idempotency_table.c.owner_user_id.is_not(None),
)
Index(
    "uq_simulation_create_idempotency_workspace_key",
    simulation_create_idempotency_table.c.actor_user_id,
    simulation_create_idempotency_table.c.organization_id,
    simulation_create_idempotency_table.c.workspace_id,
    simulation_create_idempotency_table.c.operation,
    simulation_create_idempotency_table.c.idempotency_key,
    unique=True,
    sqlite_where=simulation_create_idempotency_table.c.workspace_id.is_not(None),
    postgresql_where=simulation_create_idempotency_table.c.workspace_id.is_not(None),
)
Index("ix_simulation_create_idempotency_resource", simulation_create_idempotency_table.c.simulation_resource_id)
Index("ix_simulation_create_idempotency_status_lease", simulation_create_idempotency_table.c.status, simulation_create_idempotency_table.c.lease_expires_at)
