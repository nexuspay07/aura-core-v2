from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import datetime
import random

router = APIRouter(prefix="/phase90", tags=["Phase 90 — Global Intelligence Network"])


# INPUT
class AuraNode(BaseModel):
    node_id: str
    intelligence_score: float
    active_goals: int
    system_load: float


class Phase90Input(BaseModel):
    nodes: List[AuraNode]


# OUTPUT
class NodeStatus(BaseModel):
    node_id: str
    synchronized: bool
    optimization_factor: float
    stability_score: float


class Phase90Output(BaseModel):
    message: str
    network_status: List[NodeStatus]
    global_intelligence_score: float
    network_stability_score: float
    total_active_nodes: int
    timestamp: str


class GlobalIntelligenceEngine:

    def synchronize(self, nodes):

        statuses = []

        total_intelligence = 0
        total_stability = 0

        for node in nodes:

            optimization_factor = round(
                node.intelligence_score * (1 - node.system_load),
                3
            )

            stability = round(
                (optimization_factor + (1 - node.system_load)) / 2,
                3
            )

            synchronized = optimization_factor > 0.5

            total_intelligence += node.intelligence_score
            total_stability += stability

            statuses.append(
                NodeStatus(
                    node_id=node.node_id,
                    synchronized=synchronized,
                    optimization_factor=optimization_factor,
                    stability_score=stability
                )
            )

        global_score = round(
            total_intelligence / len(nodes), 3
        ) if nodes else 0

        stability_score = round(
            total_stability / len(nodes), 3
        ) if nodes else 0

        return statuses, global_score, stability_score


engine = GlobalIntelligenceEngine()


@router.post("/synchronize", response_model=Phase90Output)
def synchronize(data: Phase90Input):

    statuses, global_score, stability_score = engine.synchronize(data.nodes)

    return Phase90Output(
        message="Phase 90 global intelligence network synchronized",
        network_status=statuses,
        global_intelligence_score=global_score,
        network_stability_score=stability_score,
        total_active_nodes=len(data.nodes),
        timestamp=str(datetime.datetime.now())
    )