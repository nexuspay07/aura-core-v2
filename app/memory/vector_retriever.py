from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory


def retrieve_relevant_memories(tenant_id, domain, query, limit=5):

    db = SessionLocal()

    try:

        # SIMPLE and RELIABLE retrieval first (no vector filtering yet)
        memories = (
            db.query(ConversationMemory)
            .filter(ConversationMemory.tenant_id == tenant_id)
            .filter(ConversationMemory.domain == domain)
            .order_by(ConversationMemory.created_at.desc())
            .limit(limit)
            .all()
        )

        return memories

    finally:
        db.close()
