from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class BusinessProfile(Base):

    __tablename__ = "business_profiles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        unique=True,
        nullable=False
    )

    business_name = Column(
        String,
        nullable=False
    )

    industry = Column(
        String,
        nullable=False
    )

    business_stage = Column(
        String,
        default="startup"
    )

    description = Column(
        Text,
        default=""
    )

    mission = Column(
        Text,
        default=""
    )

    vision = Column(
        Text,
        default=""
    )

    products_services = Column(
        Text,
        default=""
    )

    target_market = Column(
        Text,
        default=""
    )

    business_goals = Column(
        Text,
        default=""
    )

    current_challenges = Column(
        Text,
        default=""
    )

    competitive_advantage = Column(
        Text,
        default=""
    )

    website = Column(
        String,
        default=""
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    workspace = relationship(
        "Workspace"
    )