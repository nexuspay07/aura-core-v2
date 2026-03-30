from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.knowledge_models import Knowledge



def store_knowledge(tenant_id, domain, fact_type, fact_value):

    db = SessionLocal()

    try:

        knowledge = KnowledgeBase(
            tenant_id=tenant_id,
            domain=domain,
            fact_type=fact_type,
            fact_value=fact_value
        )

        db.add(knowledge)
        db.commit()

    finally:
        db.close()
