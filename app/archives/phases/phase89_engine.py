from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
import datetime

router = APIRouter(prefix="/phase89", tags=["Phase 89 — Federated Intelligence Engine"])


# INPUT
class NodeKnowledge(BaseModel):
    node_id: str
    knowledge_scores: Dict[str, float]


class Phase89Input(BaseModel):
    nodes: List[NodeKnowledge]


# OUTPUT
class FederatedKnowledge(BaseModel):
    knowledge_area: str
    federated_score: float


class Phase89Output(BaseModel):
    message: str
    federated_knowledge: List[FederatedKnowledge]
    network_intelligence_score: float
    participating_nodes: int
    timestamp: str


class FederatedLearningEngine:

    def federate(self, nodes):

        combined_scores = {}
        count_scores = {}

        for node in nodes:

            for key, value in node.knowledge_scores.items():

                if key not in combined_scores:
                    combined_scores[key] = 0
                    count_scores[key] = 0

                combined_scores[key] += value
                count_scores[key] += 1

        federated = []
        total_score = 0

        for key in combined_scores:

            avg_score = round(combined_scores[key] / count_scores[key], 3)

            federated.append(
                FederatedKnowledge(
                    knowledge_area=key,
                    federated_score=avg_score
                )
            )

            total_score += avg_score

        network_score = round(total_score / len(federated), 3) if federated else 0

        return federated, network_score


engine = FederatedLearningEngine()


@router.post("/federate", response_model=Phase89Output)
def federate(data: Phase89Input):

    federated, network_score = engine.federate(data.nodes)

    return Phase89Output(
        message="Phase 89 federated intelligence synchronization complete",
        federated_knowledge=federated,
        network_intelligence_score=network_score,
        participating_nodes=len(data.nodes),
        timestamp=str(datetime.datetime.now())
    )