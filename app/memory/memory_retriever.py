import json
from typing import List

import numpy as np
from sqlalchemy.orm import Session

from app.memory.memory_repository import memory_repository
from app.memory.vector_engine import (
    embed_text,
    cosine_similarity,
)


class MemoryRetriever:

    def retrieve(
        self,
        db: Session,
        organization_id: int,
        query: str,
        limit: int = 5,
    ) -> List[dict]:

        memories = memory_repository.retrieve(
            db=db,
            organization_id=organization_id,
            limit=100,
        )

        query_vector = np.array(embed_text(query))

        scored = []

        for memory in memories:

            embedding = memory.get("embedding")

            if embedding:

                vector = np.array(json.loads(embedding))

            else:

                vector = np.array(
                    embed_text(
                        memory["content"]
                    )
                )

            score = cosine_similarity(
                query_vector,
                vector,
            )

            scored.append(
                {
                    "score": float(score),
                    "memory": memory,
                }
            )

        scored.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored[:limit]


memory_retriever = MemoryRetriever()