from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)

from app.db.database import metadata


knowledge_edge_table = Table(
    "knowledge_edges",
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
        "source_node_id",
        Integer,
        ForeignKey("knowledge_nodes.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "relation",
        String(150),
        nullable=False,
        index=True,
    ),

    Column(
        "target_node_id",
        Integer,
        ForeignKey("knowledge_nodes.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False,
    ),

    UniqueConstraint(
        "organization_id",
        "source_node_id",
        "relation",
        "target_node_id",
        name="uq_knowledge_edge",
    ),
)