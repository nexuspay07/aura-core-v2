from sqlalchemy import Table, Column, Integer, String, JSON, MetaData

metadata = MetaData()

strategies = Table(
    "strategies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("goal", String),
    Column("data", JSON),
    Column("owner", String),
    Column("is_public", Integer, default=1),  # 1 = public, 0 = private
)