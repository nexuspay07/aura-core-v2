"""Canonical durable Personal Decision product records."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Table, Text, UniqueConstraint, func

from app.db.database import metadata


personal_decision_table = Table(
    "personal_decisions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
    # Legacy-session linkage is optional. The decision retains a curated copy
    # so session deletion never removes product decision history.
    Column("source_session_id", Integer, ForeignKey("intelligence_sessions.id", ondelete="SET NULL"), nullable=True),
    Column("title", String(255), nullable=False),
    Column("original_question", Text, nullable=False),
    Column("decision_type", String(64), nullable=False),
    Column("status", String(32), nullable=False, server_default="open"),
    Column("related_goal_id", Integer, nullable=True),
    Column("analysis_snapshot_json", JSON, nullable=False),
    Column("recommendation", Text, nullable=False),
    Column("confidence", String(32), nullable=True),
    Column("confidence_rationale", Text, nullable=True),
    Column("user_choice", Text, nullable=True),
    Column("user_choice_rationale", Text, nullable=True),
    Column("decision_date", DateTime(timezone=True), nullable=True),
    Column("review_date", DateTime(timezone=True), nullable=True),
    Column("outcome_status", String(32), nullable=False, server_default="not_recorded"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    CheckConstraint("status IN ('open','decided','awaiting_outcome','completed')", name="ck_personal_decisions_status"),
    CheckConstraint("outcome_status IN ('not_recorded','pending','recorded')", name="ck_personal_decisions_outcome_status"),
    # A completed Personal Ask analysis is one durable decision source.  A
    # future deliberate duplication feature can create a new source session.
    UniqueConstraint("source_session_id", name="uq_personal_decisions_source_session"),
)

Index("ix_personal_decisions_scope_updated", personal_decision_table.c.organization_id, personal_decision_table.c.workspace_id, personal_decision_table.c.user_id, personal_decision_table.c.updated_at)
Index("ix_personal_decisions_scope_status", personal_decision_table.c.organization_id, personal_decision_table.c.workspace_id, personal_decision_table.c.status)
Index("ix_personal_decisions_review_date", personal_decision_table.c.review_date)
Index("ix_personal_decisions_source_session", personal_decision_table.c.source_session_id)
