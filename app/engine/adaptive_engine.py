# app/engine/adaptive_engine.py

from sqlalchemy.orm import Session
from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.memory_models import ConversationMemory


class AdaptiveEngine:

    def learn(self, tenant_id: str, domain: str):

        db: Session = SessionLocal()

        try:

            memories = (
                db.query(ConversationMemory)
                .filter(
                    ConversationMemory.tenant_id == tenant_id,
                    ConversationMemory.domain == domain
                )
                .order_by(ConversationMemory.created_at.desc())
                .limit(50)
                .all()
            )

            if not memories:
                return None

            patterns = []

            for memory in memories:

                if memory.user_message:
                    patterns.append(memory.user_message.lower())

            return self.extract_patterns(patterns)

        finally:
            db.close()


    def extract_patterns(self, patterns):

        identity_patterns = [
            p for p in patterns
            if "my name is" in p
        ]

        preference_patterns = [
            p for p in patterns
            if "favorite" in p
        ]

        return {
            "identity_patterns": identity_patterns,
            "preference_patterns": preference_patterns,
            "total_memories": len(patterns)
        }


adaptive_engine = AdaptiveEngine()
