from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import datetime
import random

router = APIRouter(prefix="/phase77", tags=["Phase 77 — Self-Correction & Recovery Engine"])


# INPUT
class FailedExecution(BaseModel):
    goal: str
    success: bool
    impact_score: float


class Phase77Input(BaseModel):
    execution_results: List[FailedExecution]
    system_state: Dict[str, float]


# OUTPUT
class CorrectionResult(BaseModel):
    goal: str
    corrected: bool
    correction_strength: float


class Phase77Output(BaseModel):
    message: str
    corrections_applied: List[CorrectionResult]
    recovered_state: Dict[str, float]
    timestamp: str


class SelfCorrectionEngine:

    def correct(self, execution_results, system_state):

        recovered_state = system_state.copy()
        corrections = []

        for result in execution_results:

            if not result.success:

                correction_strength = round(random.uniform(0.01, 0.04), 3)

                # Apply correction improvement
                for key in recovered_state:
                    recovered_state[key] = round(
                        min(recovered_state[key] + correction_strength, 1.0),
                        3
                    )

                corrections.append(
                    CorrectionResult(
                        goal=result.goal,
                        corrected=True,
                        correction_strength=correction_strength
                    )
                )

            else:

                corrections.append(
                    CorrectionResult(
                        goal=result.goal,
                        corrected=False,
                        correction_strength=0.0
                    )
                )

        return corrections, recovered_state


engine = SelfCorrectionEngine()


@router.post("/self-correct", response_model=Phase77Output)
def self_correct(data: Phase77Input):

    corrections, recovered_state = engine.correct(
        data.execution_results,
        data.system_state
    )

    return Phase77Output(
        message="Phase 77 self-correction complete",
        corrections_applied=corrections,
        recovered_state=recovered_state,
        timestamp=str(datetime.datetime.now())
    )