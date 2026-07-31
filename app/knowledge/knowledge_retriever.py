from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.knowledge.knowledge_repository import knowledge_repository


class KnowledgeRetriever:
    """
    High-level interface for retrieving knowledge.

    Delegates retrieval to KnowledgeRepository.
    """

    def retrieve(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
    ) -> Optional[Dict[str, Any]]:

        return knowledge_repository.retrieve_fact(
            db=db,
            organization_id=organization_id,
            fact_type=fact_type,
        )

    def exists(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
    ) -> bool:

        return (
            self.retrieve(
                db=db,
                organization_id=organization_id,
                fact_type=fact_type,
            )
            is not None
        )


knowledge_retriever = KnowledgeRetriever()