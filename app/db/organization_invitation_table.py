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


organization_invitation_table = Table(

    "organization_invitations",

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
        "email",
        String(255),
        nullable=False
    ),

    Column(
        "role",
        String(50),
        nullable=False,
        default="employee"
    ),

    Column(
        "status",
        String(30),
        nullable=False,
        default="pending"
    ),

    Column(
        "token",
        String(255),
        nullable=False,
        unique=True
    ),

    Column(
        "created_by_user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False
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