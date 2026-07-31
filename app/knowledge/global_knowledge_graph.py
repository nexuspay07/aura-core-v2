from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.knowledge.knowledge_repository import knowledge_repository


class GlobalKnowledgeGraph:
    """
    Global Knowledge Graph.

    This class manages the logical graph while delegating
    persistence to KnowledgeRepository.
    """

    # ==========================================================
    # NODES
    # ==========================================================

    def create_node(
        self,
        db: Session,
        organization_id: int,
        node_type: str,
        node_data: Dict[str, Any],
    ) -> int:

        return knowledge_repository.create_node(
            db=db,
            organization_id=organization_id,
            node_type=node_type,
            node_data=node_data,
        )

    # ==========================================================
    # EDGES
    # ==========================================================

    def create_edge(
        self,
        db: Session,
        organization_id: int,
        source_node: int,
        relation: str,
        target_node: int,
    ) -> int:

        return knowledge_repository.create_edge(
            db=db,
            organization_id=organization_id,
            source_node=source_node,
            relation=relation,
            target_node=target_node,
        )

    # ==========================================================
    # GRAPH RETRIEVAL
    # ==========================================================

    def get_nodes(
        self,
        db: Session,
        organization_id: int,
        node_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        return knowledge_repository.get_nodes(
            db=db,
            organization_id=organization_id,
            node_type=node_type,
        )

    def get_edges(
        self,
        db: Session,
        organization_id: int,
    ) -> List[Dict[str, Any]]:

        return knowledge_repository.get_edges(
            db=db,
            organization_id=organization_id,
        )

    # ==========================================================
    # COMPLETE GRAPH
    # ==========================================================

    def get_graph(
        self,
        db: Session,
        organization_id: int,
    ) -> Dict[str, Any]:

        return {
            "nodes": self.get_nodes(
                db=db,
                organization_id=organization_id,
            ),
            "edges": self.get_edges(
                db=db,
                organization_id=organization_id,
            ),
        }


global_knowledge_graph = GlobalKnowledgeGraph()