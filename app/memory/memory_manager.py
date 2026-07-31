from sqlalchemy.orm import Session

from app.memory.memory_repository import memory_repository


class MemoryManager:
    """
    Coordinates memory operations.
    """

    def store(
        self,
        db: Session,
        organization_id: int,
        content: str,
        memory_type: str = "conversation",
        **kwargs,
    ):
        return memory_repository.store(
            db=db,
            organization_id=organization_id,
            content=content,
            memory_type=memory_type,
            **kwargs,
        )

    def retrieve(
        self,
        db: Session,
        organization_id: int,
        limit: int = 50,
    ):
        return memory_repository.retrieve(
            db=db,
            organization_id=organization_id,
            limit=limit,
        )

    def get_status(self):
        return {
            "manager_status": "ACTIVE"
        }


memory_manager = MemoryManager()