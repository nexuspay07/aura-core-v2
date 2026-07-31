from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    func,
)

from app.db.database import metadata


knowledge_table = Table(
    "knowledge",
    metadata,

    Column(
        "id",
        Integer,
        primary_key=True,
    ),

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

    Column(
        "fact_type",
        String(100),
        nullable=False,
        index=True,
    ),

    Column(
        "fact_value",
        String,
        nullable=False,
    ),

    Column(
        "source",
        String(100),
        nullable=True,
    ),

    Column(
        "confidence",
        Float,
        nullable=False,
        default=1.0,
    ),

    Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False,
    ),
)