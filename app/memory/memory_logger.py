from app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory


def save_memory(tenant_id: str, domain: str, user_message: str, aura_response: str):

    db = SessionLocal()

    memory = ConversationMemory(
        tenant_id=tenant_id,
        domain=domain,
        user_message=user_message,
        aura_response=aura_response
    )

    db.add(memory)

    db.commit()

    db.close()
