from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.memory.memory_repository import memory_repository
from app.memory.memory_retriever import memory_retriever
from app.memory.vector_engine import embed_text


class MemoryService:
    """
    Orchestrates Aura's memory subsystem.
    """

    def store_memory(
        self,
        db: Session,
        organization_id: int,
        content: str,
        memory_type: str = "conversation",
        response: Optional[str] = None,
        **kwargs,
    ) -> int:

        embedding = embed_text(content)

        return memory_repository.store(
            db=db,
            organization_id=organization_id,
            content=content,
            response=response,
            memory_type=memory_type,
            embedding=str(embedding),
            **kwargs,
        )

    def retrieve_memories(
        self,
        db: Session,
        organization_id: int,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:

        return memory_retriever.retrieve(
            db=db,
            organization_id=organization_id,
            query=query,
            limit=limit,
        )

    def get_memory(
        self,
        db: Session,
        memory_id: int,
    ):

        return memory_repository.get(
            db=db,
            memory_id=memory_id,
        )

    def increment_recall(
        self,
        db: Session,
        memory_id: int,
    ):

        memory_repository.increment_recall(
            db=db,
            memory_id=memory_id,
        )


memory_service = MemoryService()