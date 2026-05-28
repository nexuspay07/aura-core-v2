import json

from app.memory.vector_engine import (
    embed_text
)

from sqlalchemy import insert

from app.db.database import SessionLocal

from app.db.conversation_memory_model import (
    conversation_memory_table
)


async def save_memory(
    tenant_id: str,
    domain: str,
    user_message: str,
    aura_response: str
):

    combined_text = (
        f"USER: {user_message}\n"
        f"AURA: {aura_response}"
    )

    embedding = embed_text(
        combined_text
    )

    embedding_json = json.dumps(
        embedding.tolist()
    )

    query = insert(
        conversation_memory_table
    ).values(
        tenant_id=tenant_id,
        domain=domain,
        user_message=user_message,
        aura_response=aura_response,
        embedding=embedding_json,
    )

    db = SessionLocal()

    try:

        db.execute(query)
        db.commit()

    finally:

        db.close()

    return {
        "saved": True
    }