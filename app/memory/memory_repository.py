from sqlalchemy.orm import Session

from app.db.memory_model import Memory


class MemoryRepository:

    def save_memory(
        self,
        db: Session,
        tenant_id: str,
        domain: str,
        message: str,
        response: str
    ):

        memory = Memory(
            tenant_id=tenant_id,
            domain=domain,
            message=message,
            response=response
        )

        db.add(memory)
        db.commit()

        return memory

    def get_recent_memories(
        self,
        db: Session,
        tenant_id: str,
        limit: int = 5
    ):

        return (
            db.query(Memory)
            .filter(Memory.tenant_id == tenant_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .all()
        )
