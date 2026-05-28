from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory


class MemoryOptimizer:

    def strengthen_memory(self, memory_id: int):

        db: Session = SessionLocal()

        try:

            memory = db.query(ConversationMemory).filter(
                ConversationMemory.id == memory_id
            ).first()

            if not memory:
                return

            memory.recall_count += 1

            memory.confidence = min(
                1.0,
                memory.confidence + 0.05
            )

            memory.importance = min(
                1.0,
                memory.importance + 0.02
            )

            memory.last_accessed = datetime.utcnow()

            db.commit()

        finally:

            db.close()


memory_optimizer = MemoryOptimizer()