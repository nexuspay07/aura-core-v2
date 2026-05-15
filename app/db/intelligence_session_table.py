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


intelligence_session_table = Table(
    "intelligence_sessions",
    metadata,

    Column("id", Integer, primary_key=True),

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False
    ),

    Column(
        "workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    ),

    Column(
        "created_by_user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False
    ),

    Column("title", String, nullable=False),
    Column("goal", Text, nullable=False),

    Column("domain", String, default="business"),
    Column("session_type", String, default="decision_analysis"),

    Column("status", String, default="completed"),  # completed, draft, archived

    Column("summary", Text, nullable=True),
    Column("recommended_move", Text, nullable=True),
    Column("risk_level", String, nullable=True),
    Column("business_model", String, nullable=True),

    Column("is_active", Boolean, default=True),

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