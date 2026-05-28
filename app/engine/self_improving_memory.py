from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory


class SelfImprovingMemoryEngine:


    def calculate_importance(self, message: str):

        message = message.lower()

        if "my name is" in message:
            return 0.95

        if "favorite" in message:
            return 0.9

        if "i am" in message:
            return 0.85

        if "remember" in message:
            return 0.9

        return 0.5


    def store_memory(self, tenant_id, domain, user_message, aura_response):

        db: Session = SessionLocal()

        try:

            importance = self.calculate_importance(user_message)

            memory = ConversationMemory(
                tenant_id=tenant_id,
                domain=domain,
                user_message=user_message,
                aura_response=aura_response,
                importance=importance,
                confidence=importance
            )

            db.add(memory)
            db.commit()

        finally:
            db.close()


    def recall_memory(self, tenant_id, domain):

        db: Session = SessionLocal()

        try:

            memory = (
                db.query(ConversationMemory)
                .filter(
                    ConversationMemory.tenant_id == tenant_id,
                    ConversationMemory.domain == domain
                )
                .order_by(
                    ConversationMemory.importance.desc(),
                    ConversationMemory.created_at.desc()
                )
                .first()
            )

            if memory:

                memory.recall_count += 1
                memory.last_accessed = datetime.utcnow()

                db.commit()

                return memory.user_message

            return None

        finally:
            db.close()


memory_engine = SelfImprovingMemoryEngine()
