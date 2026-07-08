from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class WorkspaceMember(Base):

    __tablename__ = "workspace_members"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    role = Column(
        String,
        default="member"
    )

    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    workspace = relationship(
        "Workspace"
    )

    user = relationship(
        "User"
    )