from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
import datetime

router = APIRouter(prefix="/phase74", tags=["Phase 74 — Collective Intelligence Engine"])


# INPUT
class Phase74Input(BaseModel):
    instance_decisions: Dict[str, Dict[str, float]]


# OUTPUT
class Phase74Output(BaseModel):
    message: str
    collective_decision: str
    collective_confidence: float
    participating_instances: int
    timestamp: str


class CollectiveIntelligenceEngine:

    def evaluate_collective(self, instance_decisions):

        best_instance = None
        best_score = -1

        for instance, metrics in instance_decisions.items():

            score = (
                metrics.get("accuracy", 0) +
                metrics.get("reasoning", 0) +
                metrics.get("learning", 0)
            ) / 3

            if score > best_score:
                best_score = score
                best_instance = instance

        return best_instance, best_score


engine = CollectiveIntelligenceEngine()


@router.post("/collective-decision", response_model=Phase74Output)
def collective_decision(data: Phase74Input):

    best_instance, confidence = engine.evaluate_collective(
        data.instance_decisions
    )

    return Phase74Output(
        message="Phase 74 collective intelligence decision complete",
        collective_decision=f"Selected intelligence from {best_instance}",
        collective_confidence=round(confidence, 3),
        participating_instances=len(data.instance_decisions),
        timestamp=str(datetime.datetime.now())
    )