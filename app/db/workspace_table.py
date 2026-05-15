from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text
)

from datetime import datetime, timezone

from app.db.database import metadata


workspace_table = Table(
    "workspaces",
    metadata,

    Column("id", Integer, primary_key=True),

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False
    ),

    Column("name", String, nullable=False),

    Column(
        "slug",
        String,
        unique=True,
        index=True,
        nullable=False
    ),

    Column(
        "description",
        Text,
        nullable=True
    ),

    Column(
        "workspace_type",
        String,
        default="business"
    ),

    Column(
        "created_by_user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False
    ),

    Column(
        "is_active",
        Boolean,
        default=True
    ),

    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    ),

    Column(
        "updated_at",
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    ),
)