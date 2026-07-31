from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    ForeignKey,
    func,
)

from app.db.database import metadata


simulation_history_table = Table(
    "simulation_history",
    metadata,

    Column("id", Integer, primary_key=True),

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    ),

    Column(
        "user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    ),

    Column("goal", String, nullable=False),

    Column("scenario", JSON, nullable=False),

    Column("result", JSON, nullable=False),

    Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False,
    ),
)