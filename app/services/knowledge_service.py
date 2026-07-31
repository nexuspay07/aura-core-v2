from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.knowledge.knowledge_extractor import KnowledgeExtractor
from app.knowledge.knowledge_store import knowledge_store
from app.knowledge.knowledge_retriever import knowledge_retriever
from app.knowledge.global_knowledge_graph import global_knowledge_graph


class KnowledgeService:
    """
    Service layer for Aura's Knowledge subsystem.

    Responsibilities:
    - Extract knowledge from text
    - Store extracted facts
    - Build and maintain the knowledge graph
    - Retrieve stored knowledge
    """

    def __init__(self):

        self.extractor = KnowledgeExtractor()

    # ==========================================================
    # FACT EXTRACTION
    # ==========================================================

    def extract(
        self,
        text: str,
    ):

        return self.extractor.extract(text)

    # ==========================================================
    # STORE FACT
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

        return knowledge_store.store(
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

    # ==========================================================
    # RETRIEVE FACT
    # ==========================================================

    def retrieve_fact(
        self,
        db: Session,
        organization_id: int,
        fact_type: str,
    ):

        return knowledge_retriever.retrieve(
            db=db,
            organization_id=organization_id,
            fact_type=fact_type,
        )

    # ==========================================================
    # GRAPH
    # ==========================================================

    def create_node(
        self,
        db: Session,
        organization_id: int,
        node_type: str,
        node_data: Dict[str, Any],
    ) -> int:

        return global_knowledge_graph.create_node(
            db=db,
            organization_id=organization_id,
            node_type=node_type,
            node_data=node_data,
        )

    def create_edge(
        self,
        db: Session,
        organization_id: int,
        source_node: int,
        relation: str,
        target_node: int,
    ) -> int:

        return global_knowledge_graph.create_edge(
            db=db,
            organization_id=organization_id,
            source_node=source_node,
            relation=relation,
            target_node=target_node,
        )

    def get_graph(
        self,
        db: Session,
        organization_id: int,
    ) -> Dict[str, List[Dict[str, Any]]]:

        return global_knowledge_graph.get_graph(
            db=db,
            organization_id=organization_id,
        )


knowledge_service = KnowledgeService()