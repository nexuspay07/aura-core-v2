from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.db.memory_table import memory_table


class MemoryRepository:
    """
    Repository responsible for all database access for Aura memories.
    """

    # ==========================================================
    # STORE
    # ==========================================================

    def store(
        self,
        db: Session,
        organization_id: int,
        content: str,
        memory_type: str = "conversation",
        workspace_id: Optional[int] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
        response: Optional[str] = None,
        importance: float = 1.0,
        confidence: float = 0.5,
        embedding: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> int:

        result = db.execute(
            insert(memory_table).values(
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                tenant_id=tenant_id,
                memory_type=memory_type,
                content=content,
                response=response,
                importance=importance,
                confidence=confidence,
                embedding=embedding,
                metadata=metadata,
            )
        )

        if commit:
            db.commit()

        return result.inserted_primary_key[0]

    # ==========================================================
    # RETRIEVE
    # ==========================================================

    def retrieve(
        self,
        db: Session,
        organization_id: int,
        limit: int = 50,
    ) -> List[RowMapping]:

        result = db.execute(
            select(memory_table)
            .where(
                memory_table.c.organization_id == organization_id
            )
            .order_by(
                memory_table.c.created_at.desc()
            )
            .limit(limit)
        )

        return result.mappings().all()

    # ==========================================================
    # GET
    # ==========================================================

    def get(
        self,
        db: Session,
        memory_id: int,
    ) -> Optional[RowMapping]:

        result = db.execute(
            select(memory_table)
            .where(memory_table.c.id == memory_id)
        )

        return result.mappings().first()

    # ==========================================================
    # UPDATE RECALL COUNT
    # ==========================================================

    def increment_recall(
        self,
        db: Session,
        memory_id: int,
    ) -> None:

        db.execute(
            update(memory_table)
            .where(memory_table.c.id == memory_id)
            .values(
                recall_count=memory_table.c.recall_count + 1
            )
        )

        db.commit()


memory_repository = MemoryRepository()
