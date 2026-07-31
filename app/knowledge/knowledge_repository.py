from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.knowledge_table import knowledge_table
from app.db.knowledge_node_table import knowledge_node_table
from app.db.knowledge_edge_table import knowledge_edge_table


class KnowledgeRepository:
    """
    Repository responsible for all database operations
    for Aura's knowledge subsystem.
    """

    # ==========================================================
    # FACTS
    # ==========================================================

    def store_fact(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
        fact_value: str,
        workspace_id: Optional[int] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
        source: Optional[str] = None,
        confidence: float = 1.0,
    ) -> int:

        result = db.execute(
            insert(knowledge_table).values(
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                tenant_id=tenant_id,
                fact_type=fact_type,
                fact_value=fact_value,
                source=source,
                confidence=confidence,
            )
        )

        db.commit()

        return result.inserted_primary_key[0]

    def retrieve_fact(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
    ) -> Optional[Dict[str, Any]]:

        result = db.execute(
            select(knowledge_table)
            .where(
                knowledge_table.c.organization_id
                == organization_id
            )
            .where(
                knowledge_table.c.fact_type
                == fact_type
            )
            .order_by(
                knowledge_table.c.created_at.desc()
            )
            .limit(1)
        )

        return result.mappings().first()

    # ==========================================================
    # GRAPH NODES
    # ==========================================================

    def create_node(
        self,
        db: Session,
        organization_id: int,
        node_type: str,
        node_data: Dict[str, Any],
    ) -> int:

        result = db.execute(
            insert(knowledge_node_table).values(
                organization_id=organization_id,
                node_type=node_type,
                node_data=node_data,
            )
        )

        db.commit()

        return result.inserted_primary_key[0]

    def get_nodes(
        self,
        db: Session,
        organization_id: int,
        node_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        query = select(
            knowledge_node_table
        ).where(
            knowledge_node_table.c.organization_id
            == organization_id
        )

        if node_type:

            query = query.where(
                knowledge_node_table.c.node_type
                == node_type
            )

        result = db.execute(query)

        return result.mappings().all()

    # ==========================================================
    # GRAPH EDGES
    # ==========================================================

    def create_edge(
        self,
        db: Session,
        organization_id: int,
        source_node: int,
        relation: str,
        target_node: int,
    ) -> int:

        result = db.execute(
            insert(knowledge_edge_table).values(
                organization_id=organization_id,
                source_node=source_node,
                relation=relation,
                target_node=target_node,
            )
        )

        db.commit()

        return result.inserted_primary_key[0]

    def get_edges(
        self,
        db: Session,
        organization_id: int,
    ) -> List[Dict[str, Any]]:

        result = db.execute(
            select(knowledge_edge_table)
            .where(
                knowledge_edge_table.c.organization_id
                == organization_id
            )
        )

        return result.mappings().all()


knowledge_repository = KnowledgeRepository()