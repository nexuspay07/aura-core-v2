from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from AURA.AURA_CORE_V2.app.db.database import Base


class Knowledge(Base):

    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True)

    domain = Column(String, index=True)

    content = Column(Text)

    source = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
