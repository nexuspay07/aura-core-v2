from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
)

from app.db.database import metadata


users = Table(
    "users",
    metadata,

    Column("id", Integer, primary_key=True),

    Column("username", String, unique=True),
    Column("email", String, unique=True),

    Column("password", String),

    # AURA PLANS
    Column("plan", String, default="free"),

    # free
    # pro
    # business
    # enterprise

    Column(
        "subscription_status",
        String,
        default="inactive"
    ),

    Column(
        "stripe_customer_id",
        String,
        nullable=True
    ),

    Column(
        "is_active",
        Boolean,
        default=True
    ),
)