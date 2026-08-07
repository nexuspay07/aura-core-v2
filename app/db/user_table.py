from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone

from app.db.database import metadata


user_table = Table(
    "users",
    metadata,

    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("password_hash", String, nullable=False),

    # Server-controlled canonical authenticated context.  The organization is
    # always derived from this workspace rather than stored separately.
    Column(
        "active_workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    ),

    Column("full_name", String, nullable=True),
    Column("role", String, default="user"),

    # SUBSCRIPTIONS

Column(
    "plan",
    String,
    default="free"
),

Column(
    "subscription_status",
    String,
    default="inactive"
),

Column(
    "payment_provider",
    String,
    nullable=True
),

Column(
    "external_customer_id",
    String,
    nullable=True
),

    Column("is_active", Boolean, default=True),
    Column("is_verified", Boolean, default=False),

    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime, default=lambda: datetime.now(timezone.utc)),

    
)
