from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone

from app.db.database import metadata


organization_table = Table(
    "organizations",
    metadata,

    Column("id", Integer, primary_key=True),

    Column("name", String, nullable=False),
    Column("slug", String, unique=True, index=True, nullable=False),

    Column("owner_user_id", Integer, ForeignKey("users.id"), nullable=False),

    Column("plan", String, default="free"),  # free, pro, business, enterprise
    Column("industry", String, nullable=True),
    Column("company_size", String, nullable=True),

    Column("is_active", Boolean, default=True),

    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)