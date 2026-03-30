from sqlalchemy import Table, Column, Integer, String, JSON, DateTime
from datetime import datetime
from app.db.database import metadata

simulations = Table(
    "simulations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("goal", String),
    Column("result", JSON),
    Column("owner", String),
    Column("created_at", DateTime, default=datetime.utcnow)
)