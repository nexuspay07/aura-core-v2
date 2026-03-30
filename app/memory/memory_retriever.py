from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory
from app.memory.vector_engine import embed_text, cosine_similarity


def retrieve_relevant_memories(tenant_id, domain, query, limit=5):

    db = SessionLocal()

    memories = (
        db.query(ConversationMemory)
        .filter(
            ConversationMemory.tenant_id == tenant_id,
            ConversationMemory.domain == domain
        )
        .all()
    )

    db.close()

    query_vector = embed_text(query)

    scored_memories = []

    for memory in memories:

        memory_vector = embed_text(memory.user_message)

        score = cosine_similarity(query_vector, memory_vector)

        scored_memories.append((score, memory))

    scored_memories.sort(key=lambda x: x[0], reverse=True)

    top_memories = [m[1] for m in scored_memories[:limit]]

    return top_memories
