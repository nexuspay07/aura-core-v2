from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
import datetime

router = APIRouter(prefix="/phase73", tags=["Phase 73 — Distributed Learning Engine"])


# INPUT MODEL
class Phase73Input(BaseModel):
    instance_results: Dict[str, Dict[str, float]]


# OUTPUT MODEL
class Phase73Output(BaseModel):
    message: str
    global_learning: Dict[str, float]
    improvement_factor: float
    timestamp: str


class DistributedLearningEngine:

    def combine_learning(self, instance_results):

        combined = {
            "accuracy": 0,
            "reasoning": 0,
            "learning": 0
        }

        count = len(instance_results)

        if count == 0:
            return combined, 0

        for instance, metrics in instance_results.items():

            combined["accuracy"] += metrics.get("accuracy", 0)
            combined["reasoning"] += metrics.get("reasoning", 0)
            combined["learning"] += metrics.get("learning", 0)

        combined["accuracy"] /= count
        combined["reasoning"] /= count
        combined["learning"] /= count

        improvement_factor = (
            combined["accuracy"]
            + combined["reasoning"]
            + combined["learning"]
        ) / 3

        return combined, improvement_factor


engine = DistributedLearningEngine()


@router.post("/distributed-learn", response_model=Phase73Output)
def distributed_learn(data: Phase73Input):

    combined, improvement = engine.combine_learning(data.instance_results)

    return Phase73Output(
        message="Phase 73 distributed learning complete",
        global_learning=combined,
        improvement_factor=round(improvement, 3),
        timestamp=str(datetime.datetime.now())
    )