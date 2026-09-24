"""Canonical durable Strategy resources and immutable revisions."""

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


strategy_resource_table = Table(
    "strategy_resources",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(36), nullable=False),
    Column("title", String(255), nullable=False),
    Column("created_by_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("owner_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
    Column("current_revision_number", Integer, nullable=False, default=1, server_default="1"),
    Column("lock_version", Integer, nullable=False, default=1, server_default="1"),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    UniqueConstraint("public_id", name="uq_strategy_resources_public_id"),
    CheckConstraint("length(trim(title)) > 0", name="ck_strategy_resources_title_nonempty"),
    CheckConstraint("current_revision_number > 0", name="ck_strategy_resources_current_revision_positive"),
    CheckConstraint("lock_version > 0", name="ck_strategy_resources_lock_version_positive"),
    CheckConstraint(
        "(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR "
        "(owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)",
        name="ck_strategy_resources_tenancy_shape",
    ),
)

Index(
    "ix_strategy_resources_owner_archive_updated",
    strategy_resource_table.c.owner_user_id,
    strategy_resource_table.c.archived_at,
    strategy_resource_table.c.updated_at,
)
Index(
    "ix_strategy_resources_workspace_archive_updated",
    strategy_resource_table.c.organization_id,
    strategy_resource_table.c.workspace_id,
    strategy_resource_table.c.archived_at,
    strategy_resource_table.c.updated_at,
)
Index("ix_strategy_resources_created_by", strategy_resource_table.c.created_by_user_id)


strategy_revision_table = Table(
    "strategy_revisions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("strategy_id", Integer, ForeignKey("strategy_resources.id", ondelete="CASCADE"), nullable=False),
    Column("revision_number", Integer, nullable=False),
    Column("canonical_result_json", JSON, nullable=False),
    Column("snapshot_schema_version", Integer, nullable=False, default=1, server_default="1"),
    Column("created_by_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("origin_type", String(32), nullable=False),
    Column("source_decision_id", Integer, ForeignKey("personal_decisions.id", ondelete="SET NULL"), nullable=True),
    Column("source_decision_snapshot_id", Integer, ForeignKey("decision_execution_snapshots.id", ondelete="RESTRICT"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("strategy_id", "revision_number", name="uq_strategy_revisions_strategy_revision"),
    CheckConstraint("revision_number > 0", name="ck_strategy_revisions_revision_positive"),
    CheckConstraint("snapshot_schema_version > 0", name="ck_strategy_revisions_snapshot_schema_version_positive"),
    CheckConstraint("origin_type IN ('direct', 'decision_derived')", name="ck_strategy_revisions_origin_type"),
    CheckConstraint(
        "origin_type = 'decision_derived' OR (source_decision_id IS NULL AND source_decision_snapshot_id IS NULL)",
        name="ck_strategy_revisions_direct_source_decision",
    ),
)

Index("ix_strategy_revisions_strategy_created", strategy_revision_table.c.strategy_id, strategy_revision_table.c.created_at)
Index("ix_strategy_revisions_source_decision", strategy_revision_table.c.source_decision_id)
Index("ix_strategy_revisions_source_decision_snapshot", strategy_revision_table.c.source_decision_snapshot_id)
