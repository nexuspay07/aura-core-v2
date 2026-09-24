"""Immutable canonical Decision execution snapshots."""
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Table, UniqueConstraint, func
from app.db.database import metadata

decision_execution_snapshot_table = Table(
    "decision_execution_snapshots", metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(36), nullable=False),
    Column("intelligence_session_id", Integer, ForeignKey("intelligence_sessions.id", ondelete="SET NULL"), nullable=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
    Column("snapshot_version", Integer, nullable=False),
    Column("snapshot_schema_version", Integer, nullable=False, server_default="1"),
    Column("canonical_decision_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("public_id", name="uq_decision_execution_snapshots_public_id"),
    UniqueConstraint("intelligence_session_id", "snapshot_version", name="uq_decision_execution_snapshots_session_version"),
    CheckConstraint("length(trim(public_id)) > 0", name="ck_decision_execution_snapshots_public_id_nonempty"),
    CheckConstraint("snapshot_version > 0", name="ck_decision_execution_snapshots_version_positive"),
    CheckConstraint("snapshot_schema_version > 0", name="ck_decision_execution_snapshots_schema_version_positive"),
)
Index("ix_decision_execution_snapshots_scope_session", decision_execution_snapshot_table.c.user_id, decision_execution_snapshot_table.c.organization_id, decision_execution_snapshot_table.c.workspace_id, decision_execution_snapshot_table.c.intelligence_session_id)
