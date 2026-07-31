from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)

from app.db.database import metadata


workspace_member_table = Table(
    "workspace_members",
    metadata,

    # ==========================================================
    # PRIMARY KEY
    # ==========================================================

    Column(
        "id",
        Integer,
        primary_key=True,
    ),

    # ==========================================================
    # RELATIONSHIPS
    # ==========================================================

    Column(
        "workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),

    # ==========================================================
    # MEMBERSHIP
    # ==========================================================

    Column(
        "role",
        String(50),
        nullable=False,
        default="member",
        index=True,
    ),

    Column(
        "status",
        String(30),
        nullable=False,
        default="active",
    ),

    Column(
        "is_active",
        Boolean,
        nullable=False,
        default=True,
        index=True,
    ),

    # ==========================================================
    # AUDIT
    # ==========================================================

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),

    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),

    # ==========================================================
    # CONSTRAINTS
    # ==========================================================

    UniqueConstraint(
        "workspace_id",
        "user_id",
        name="uq_workspace_member",
    ),
)