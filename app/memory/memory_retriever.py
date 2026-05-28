import json
import numpy as np

from sqlalchemy import select

from app.db.database import SessionLocal

from app.db.conversation_memory_model import (
    conversation_memory_table
)

from app.memory.vector_engine import (
    embed_text,
    cosine_similarity,
)


async def retrieve_relevant_memories(
    tenant_id,
    domain,
    query,
    limit=5
):

    db = SessionLocal()

    try:

        result = db.execute(
            select(conversation_memory_table)
            .where(
                conversation_memory_table.c.tenant_id
                == tenant_id
            )
            .where(
                conversation_memory_table.c.domain
                == domain
            )
        )

        rows = result.fetchall()

    finally:

        db.close()

    query_vector = embed_text(query)

    scored_memories = []

    for memory in rows:

        memory_data = dict(memory._mapping)

        if memory_data["embedding"]:

            memory_vector = np.array(
                json.loads(memory_data["embedding"])
            )

        else:

            memory_vector = embed_text(
                memory_data["user_message"]
            )

        score = cosine_similarity(
            query_vector,
            memory_vector
        )

        scored_memories.append({
            "score": float(score),
            "memory": memory_data
        })

    scored_memories.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return scored_memories[:limit]