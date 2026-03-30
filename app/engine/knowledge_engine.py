from sqlalchemy.orm import Session
from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.knowledge_models import Knowledge


class KnowledgeEngine:

    def get_knowledge(self, tenant_id: str, domain: str):

        db: Session = SessionLocal()

        try:

            result = (
                db.query(Knowledge)
                .filter(
                    Knowledge.tenant_id == tenant_id,
                    Knowledge.domain == domain
                )
                .order_by(Knowledge.created_at.desc())
                .first()
            )

            if result:
                return result.content

            return None

        finally:

            db.close()


knowledge_engine = KnowledgeEngine()
