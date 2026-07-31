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


organization_invitation_table = Table(
    "organization_invitations",
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
    # INVITATION
    # ==========================================================

    Column(
        "email",
        String(255),
        nullable=False,
        index=True,
    ),

    Column(
        "role",
        String(50),
        nullable=False,
        default="employee",
    ),

    Column(
        "status",
        String(30),
        nullable=False,
        default="pending",
        index=True,
    ),

    Column(
        "token",
        String(255),
        nullable=False,
        unique=True,
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

    # ==========================================================
    # CONSTRAINTS
    # ==========================================================

    UniqueConstraint(
        "organization_id",
        "email",
        name="uq_organization_invitation_email",
    ),
)