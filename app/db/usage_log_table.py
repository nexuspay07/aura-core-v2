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