# app/engine/phase72_engine.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import random
import datetime

router = APIRouter(
    prefix="/phase72",
    tags=["Phase 72 — Distributed Reasoning Engine"]
)


class InstanceReasoningInput(BaseModel):
    instance_id: str
    reasoning_strength: float


class Phase72Input(BaseModel):
    problem: str
    instances: List[InstanceReasoningInput]


class InstanceContribution(BaseModel):
    instance_id: str
    contribution_score: float
    insight: str


class Phase72Output(BaseModel):
    message: str
    problem: str
    contributions: List[InstanceContribution]
    collective_confidence: float
    timestamp: str


class DistributedReasoningEngine:

    def reason(self, problem: str, instances: List[InstanceReasoningInput]):

        contributions = []
        total_score = 0

        for instance in instances:

            contribution_score = min(
                instance.reasoning_strength * random.uniform(0.9, 1.1),
                1.0
            )

            insight = f"{instance.instance_id} contributed reasoning on '{problem}'"

            contributions.append(
                InstanceContribution(
                    instance_id=instance.instance_id,
                    contribution_score=round(contribution_score, 4),
                    insight=insight
                )
            )

            total_score += contribution_score

        collective_confidence = round(total_score / len(instances), 4)

        return contributions, collective_confidence


engine = DistributedReasoningEngine()


@router.post("/reason", response_model=Phase72Output)
def distributed_reason(data: Phase72Input):

    contributions, confidence = engine.reason(
        data.problem,
        data.instances
    )

    return Phase72Output(
        message="Phase 72 distributed reasoning complete",
        problem=data.problem,
        contributions=contributions,
        collective_confidence=confidence,
        timestamp=datetime.datetime.utcnow().isoformat()
    )