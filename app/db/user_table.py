from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone

from app.db.database import metadata


user_table = Table(
    "users",
    metadata,

    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("password_hash", String, nullable=False),

    Column("full_name", String, nullable=True),
    Column("role", String, default="user"),

    Column("is_active", Boolean, default=True),
    Column("is_verified", Boolean, default=False),

    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)