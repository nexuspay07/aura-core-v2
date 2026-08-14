from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    JSON,
    MetaData
)

metadata = MetaData()

strategies = Table(
    "strategies",
    metadata,

    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("goal", String),
    Column("data", JSON),
    Column("owner", String),
    Column("is_public", Integer, default=1),
    Column("owner_user_id", Integer, nullable=True, index=True),
    Column("organization_id", Integer, nullable=True, index=True),
    Column("workspace_id", Integer, nullable=True, index=True),
    Column("description", String, nullable=True),
    Column("category", String(32), nullable=False, default="strategy"),
    Column("item_type", String(32), nullable=False, default="strategy"),
    Column("created_at", String, nullable=True),
    Column("updated_at", String, nullable=True),
)
