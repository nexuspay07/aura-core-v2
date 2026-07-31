from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    ForeignKey,
    func,
)

from app.db.database import metadata


knowledge_node_table = Table(
    "knowledge_nodes",
    metadata,

    Column(
        "id",
        Integer,
        primary_key=True,
    ),

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "node_type",
        String(100),
        nullable=False,
        index=True,
    ),

    Column(
        "node_data",
        JSON,
        nullable=False,
    ),

    Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False,
    ),
)