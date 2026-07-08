from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey
)

from datetime import (
    datetime,
    timezone
)

from app.db.database import metadata


business_profile_table = Table(

    "business_profiles",

    metadata,

    # -------------------------------------------------
    # PRIMARY KEY
    # -------------------------------------------------

    Column(
        "id",
        Integer,
        primary_key=True
    ),

    # -------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------

    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    ),

    Column(
        "workspace_id",
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        unique=True,
        index=True
    ),

    # -------------------------------------------------
    # COMPANY IDENTITY
    # -------------------------------------------------

    Column(
        "business_name",
        String,
        nullable=False
    ),

    Column(
        "legal_name",
        String,
        nullable=True
    ),

    Column(
        "industry",
        String,
        nullable=True
    ),

    Column(
        "business_stage",
        String,
        nullable=False,
        default="startup"
    ),

    Column(
        "business_model",
        String,
        nullable=True
    ),

    # -------------------------------------------------
    # COMPANY PURPOSE
    # -------------------------------------------------

    Column(
        "mission",
        Text,
        nullable=True
    ),

    Column(
        "vision",
        Text,
        nullable=True
    ),

    Column(
        "description",
        Text,
        nullable=True
    ),

    # -------------------------------------------------
    # MARKET
    # -------------------------------------------------

    Column(
        "target_market",
        Text,
        nullable=True
    ),

    Column(
        "target_customer",
        Text,
        nullable=True
    ),

    Column(
        "geographic_focus",
        Text,
        nullable=True
    ),

    # -------------------------------------------------
    # PRODUCTS
    # -------------------------------------------------

    Column(
        "products_services",
        Text,
        nullable=True
    ),

    Column(
        "pricing_model",
        String,
        nullable=True
    ),

    # -------------------------------------------------
    # STRATEGY
    # -------------------------------------------------

    Column(
        "business_goals",
        Text,
        nullable=True
    ),

    Column(
        "current_challenges",
        Text,
        nullable=True
    ),

    Column(
        "competitive_advantage",
        Text,
        nullable=True
    ),

    # -------------------------------------------------
    # DIGITAL
    # -------------------------------------------------

    Column(
        "website",
        String,
        nullable=True
    ),

    Column(
        "email",
        String,
        nullable=True
    ),

    Column(
        "phone",
        String,
        nullable=True
    ),

    # -------------------------------------------------
    # AI PREFERENCES
    # -------------------------------------------------

    Column(
        "preferred_language",
        String,
        nullable=True
    ),

    Column(
        "preferred_response_style",
        String,
        nullable=True
    ),

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    Column(
        "is_active",
        Boolean,
        default=True
    ),

    # -------------------------------------------------
    # AUDIT
    # -------------------------------------------------

    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(
            timezone.utc
        )
    ),

    Column(
        "updated_at",
        DateTime,
        default=lambda: datetime.now(
            timezone.utc
        )
    )

)