from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    func,
)

from app.db.database import metadata


workspace_table = Table(
    "workspaces",
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
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    ),

    Column(
        "created_by_user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),

    # ==========================================================
    # WORKSPACE DETAILS
    # ==========================================================

    Column(
        "name",
        String(255),
        nullable=False,
    ),

    Column(
        "slug",
        String(255),
        nullable=False,
        unique=True,
        index=True,
    ),

    Column(
        "description",
        Text,
        nullable=True,
    ),

    Column(
        "workspace_type",
        String(50),
        nullable=False,
        default="business",
        index=True,
    ),

    # ==========================================================
    # STATUS
    # ==========================================================

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
)