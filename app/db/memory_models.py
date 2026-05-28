# app/db/memory_models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text
)

from datetime import datetime

from app.db.database import Base


class ConversationMemory(Base):

    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True)

    domain = Column(String, index=True)

    user_message = Column(Text)

    aura_response = Column(Text)

    importance = Column(Float, default=1.0)

    confidence = Column(Float, default=0.5)

    recall_count = Column(Integer, default=0)

    embedding = Column(Text, nullable=True)

    last_accessed = Column(
        DateTime,
        default=datetime.utcnow
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )