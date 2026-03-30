from sqlalchemy import Table, Column, Integer, String, JSON, DateTime
from datetime import datetime
from .database import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True),
    Column("password", String),
)

simulation_history = Table(
    "simulation_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("goal", String),
    Column("scenario", JSON),
    Column("results", JSON),
    Column("agents", JSON),
    Column("events", JSON),
    Column("explanation", JSON),
    Column("timestamp", DateTime, default=datetime.utcnow)
)
from fastapi import Depends, HTTPException

fake_users_db = {
    "blaise": {"id": 1, "username": "blaise"},
    "guest": {"id": 0, "username": "guest"}
}

def get_current_user(username: str = "guest"):
    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user