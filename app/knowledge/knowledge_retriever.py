from app.db.database import SessionLocal
from app.db.knowledge_models import Knowledge



def retrieve_knowledge(tenant_id, domain, fact_type):

    db = SessionLocal()

    try:

        knowledge = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.tenant_id == tenant_id)
            .filter(KnowledgeBase.domain == domain)
            .filter(KnowledgeBase.fact_type == fact_type)
            .order_by(KnowledgeBase.created_at.desc())
            .first()
        )

        return knowledge

    finally:
        db.close()
