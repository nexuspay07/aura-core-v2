# app/db/memory_models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from AURA.AURA_CORE_V2.app.db.database import Base

class ConversationMemory(Base):
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    domain = Column(String, index=True)
    user_message = Column(String)
    aura_response = Column(String)
    importance = Column(Float, default=1.0)
    confidence = Column(Float, default=0.5)
    recall_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)