from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(prefix="/phase88", tags=["Phase 88 — Continuous Self-Improvement"])


# INPUT
class ExecutionFeedback(BaseModel):
    system_name: str
    success_rate: float
    anomaly_detected: bool


class Phase88Input(BaseModel):
    execution_results: List[ExecutionFeedback]


# OUTPUT
class ImprovementAdjustment(BaseModel):
    system_name: str
    improvement_factor: float
    learning_rate_adjustment: float
    action_required: str


class Phase88Output(BaseModel):
    message: str
    adjustments: List[ImprovementAdjustment]
    global_adaptation_score: float
    timestamp: str


class SelfImprovementEngine:

    def adapt(self, execution_results):

        adjustments = []
        total_adaptation = 0

        for result in execution_results:

            if result.anomaly_detected:
                improvement_factor = round(1.2 - result.success_rate, 3)
                learning_rate = round(0.1 + (1 - result.success_rate), 3)
                action_required = "Increase monitoring and corrective optimization"
            else:
                improvement_factor = round(1 - result.success_rate, 3)
                learning_rate = round(0.05 + (1 - result.success_rate) * 0.5, 3)
                action_required = "Minor optimization adjustments"

            total_adaptation += improvement_factor

            adjustments.append(
                ImprovementAdjustment(
                    system_name=result.system_name,
                    improvement_factor=improvement_factor,
                    learning_rate_adjustment=learning_rate,
                    action_required=action_required
                )
            )

        global_score = round(total_adaptation / len(execution_results), 3) if execution_results else 0.0

        return adjustments, global_score


engine = SelfImprovementEngine()


@router.post("/self-improve", response_model=Phase88Output)
def self_improve(data: Phase88Input):

    adjustments, score = engine.adapt(data.execution_results)

    return Phase88Output(
        message="Phase 88 continuous self-improvement cycle complete",
        adjustments=adjustments,
        global_adaptation_score=score,
        timestamp=str(datetime.datetime.now())
    )