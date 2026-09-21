from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    func,
    Index,
)

from app.db.database import metadata


usage_log_table = Table(
    "usage_logs",
    metadata,

    # ==========================================================
    # PRIMARY KEY
    # ==========================================================

    Column(
        "id",
        Integer,
        primary_key=True,
    ),
    Column("request_id", String(36), nullable=True, unique=True, index=True),
    Column("route", String(100), nullable=True, index=True),
    Column("request_mode", String(64), nullable=True),
    Column("outcome", String(32), nullable=True, index=True),
    Column("error_category", String(64), nullable=True),
    Column("provider", String(64), nullable=True),

    # ==========================================================
    # RELATIONSHIPS
    # ==========================================================

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    ),

    Column(
        "workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    ),

    Column(
        "user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    ),
    Column("session_id", Integer, ForeignKey("intelligence_sessions.id"), nullable=True, index=True),

    # ==========================================================
    # TENANT
    # ==========================================================

    Column(
        "tenant_id",
        String(100),
        nullable=True,
        index=True,
    ),

    Column(
        "domain",
        String(100),
        nullable=True,
        index=True,
    ),

    # ==========================================================
    # REQUEST / RESPONSE
    # ==========================================================

    Column(
        "message",
        Text,
        nullable=True,
    ),

    Column(
        "response",
        Text,
        nullable=True,
    ),

    # ==========================================================
    # EXECUTION
    # ==========================================================

    Column(
        "success",
        Boolean,
        nullable=False,
        default=True,
    ),

    Column(
        "latency_ms",
        Integer,
        nullable=True,
    ),

    Column(
        "model",
        String(100),
        nullable=True,
    ),

    Column(
        "tokens_used",
        Integer,
        nullable=True,
    ),
    Column("input_tokens", Integer, nullable=True),
    Column("output_tokens", Integer, nullable=True),
    Column("reasoning_tokens", Integer, nullable=True),
    Column("provider_latency_ms", Integer, nullable=True),
    Column("retry_count", Integer, nullable=True),
    Column("provider_call_count", Integer, nullable=True),

    # ==========================================================
    # AUDIT
    # ==========================================================

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

Index("ix_usage_logs_created_at", usage_log_table.c.created_at)
