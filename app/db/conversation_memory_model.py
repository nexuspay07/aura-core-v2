from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
)

from datetime import datetime
import uuid

from app.db.database import metadata
from sqlalchemy.sql import func
from sqlalchemy import Table


conversation_memory_table = Table(
    "conversation_memory",
    metadata,

    Column(
        "id",
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    ),

    Column(
        "tenant_id",
        String,
        nullable=False
    ),

    Column(
        "domain",
        String,
        nullable=False
    ),

    Column(
        "user_message",
        Text,
        nullable=False
    ),

    Column(
        "aura_response",
        Text,
        nullable=False
    ),

    # FUTURE VECTOR STORAGE
    Column(
        "embedding",
        Text,
        nullable=True
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now()
    ),
)