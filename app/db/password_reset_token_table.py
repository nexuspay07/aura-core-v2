from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table

from app.db.database import metadata


password_reset_token_table = Table(
    "password_reset_tokens",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_password_reset_tokens_user_created", "user_id", "created_at"),
    Index("ix_password_reset_tokens_expires_at", "expires_at"),
)
