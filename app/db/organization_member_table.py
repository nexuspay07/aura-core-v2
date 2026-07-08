from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func
)

from app.db.database import metadata


organization_member_table = Table(

    "organization_members",

    metadata,

    Column(
        "id",
        Integer,
        primary_key=True
    ),

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False
    ),

    Column(
        "user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False
    ),

    Column(
        "role",
        String(50),
        nullable=False,
        default="member"
    ),

    Column(
        "status",
        String(30),
        nullable=False,
        default="active"
    ),

    Column(
        "is_active",
        Boolean,
        nullable=False,
        default=True
    ),

    Column(
        "created_at",
        DateTime,
        server_default=func.now()
    )
)