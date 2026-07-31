from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    func,
)

from app.db.database import metadata


memory_table = Table(
    "memory",
    metadata,

    # ==========================================================
    # PRIMARY KEY
    # ==========================================================

    Column(
        "id",
        Integer,
        primary_key=True,
        autoincrement=True,
    ),

    # ==========================================================
    # ORGANIZATION
    # ==========================================================

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
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

    Column(
        "tenant_id",
        String(100),
        nullable=True,
        index=True,
    ),

    # ==========================================================
    # MEMORY CONTENT
    # ==========================================================

    Column(
        "memory_type",
        String(50),
        nullable=False,
        server_default="conversation",
    ),

    Column(
        "content",
        Text,
        nullable=False,
    ),

    Column(
        "response",
        Text,
        nullable=True,
    ),

    # ==========================================================
    # AI METADATA
    # ==========================================================

    Column(
        "importance",
        Float,
        nullable=False,
        server_default="1.0",
    ),

    Column(
        "confidence",
        Float,
        nullable=False,
        server_default="0.5",
    ),

    Column(
        "recall_count",
        Integer,
        nullable=False,
        server_default="0",
    ),

    Column(
        "embedding",
        Text,
        nullable=True,
    ),

    Column(
        "metadata",
        JSON,
        nullable=True,
    ),

    # ==========================================================
    # TIMESTAMPS
    # ==========================================================

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),

    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),

    Column(
        "last_accessed",
        DateTime(timezone=True),
        nullable=True,
    ),
)


Index(
    "idx_memory_org_workspace",
    memory_table.c.organization_id,
    memory_table.c.workspace_id,
)

Index(
    "idx_memory_type",
    memory_table.c.memory_type,
)

Index(
    "idx_memory_created",
    memory_table.c.created_at,
)