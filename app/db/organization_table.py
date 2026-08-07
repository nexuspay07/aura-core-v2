from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    CheckConstraint,
)

from app.db.database import metadata


organization_table = Table(
    "organizations",
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
    # ORGANIZATION DETAILS
    # ==========================================================

    Column(
        "name",
        String(255),
        nullable=False,
    ),

    Column(
        "slug",
        String(255),
        unique=True,
        index=True,
        nullable=False,
    ),

    Column(
        "account_type",
        String(20),
        nullable=False,
        server_default="business",
        index=True,
    ),

    CheckConstraint(
        "account_type IN ('personal', 'business', 'enterprise')",
        name="ck_organizations_account_type",
    ),

    # ==========================================================
    # OWNER
    # ==========================================================

    Column(
        "owner_user_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),

    # ==========================================================
    # SUBSCRIPTION
    # ==========================================================

    Column(
        "plan",
        String(50),
        nullable=False,
        default="free",
        index=True,
    ),

    Column(
        "subscription_status",
        String(50),
        nullable=False,
        default="inactive",
        index=True,
    ),

    Column(
        "payment_provider",
        String(100),
        nullable=True,
    ),

    Column(
        "external_subscription_id",
        String(255),
        nullable=True,
    ),

    # ==========================================================
    # BUSINESS PROFILE
    # ==========================================================

    Column(
        "industry",
        String(100),
        nullable=True,
    ),

    Column(
        "company_size",
        String(50),
        nullable=True,
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
