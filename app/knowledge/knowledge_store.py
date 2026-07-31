from sqlalchemy.orm import Session

from app.knowledge.knowledge_repository import knowledge_repository


class KnowledgeStore:
    """
    High-level interface for storing knowledge.

    Delegates persistence to KnowledgeRepository.
    """

    def store(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
        fact_value: str,
        workspace_id: int | None = None,
        user_id: int | None = None,
        tenant_id: str | None = None,
        source: str | None = None,
        confidence: float = 1.0,
    ) -> int:

        return knowledge_repository.store_fact(
            db=db,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            tenant_id=tenant_id,
            fact_type=fact_type,
            fact_value=fact_value,
            source=source,
            confidence=confidence,
        )


knowledge_store = KnowledgeStore()