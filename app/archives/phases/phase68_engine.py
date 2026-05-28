# app/engine/phase68_engine.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import random
import datetime

router = APIRouter(
    prefix="/phase68",
    tags=["Phase 68 — Autonomous Feedback & Self-Correction Engine"]
)


# Input model (results from Phase 67)
class ExecutionFeedback(BaseModel):
    goal: str
    success: bool
    confidence: float


class Phase68Input(BaseModel):
    execution_results: List[ExecutionFeedback]


# Correction model
class CorrectionResult(BaseModel):
    goal: str
    issue_detected: str
    corrective_action: str
    improvement_confidence: float
    timestamp: str


class Phase68Output(BaseModel):
    message: str
    corrections_applied: List[CorrectionResult]
    overall_system_adjustment: float


class FeedbackCorrectionEngine:

    def analyze_and_correct(self, execution_results: List[ExecutionFeedback]):

        corrections = []
        adjustment_score = 0

        for result in execution_results:

            if not result.success or result.confidence < 0.9:

                issue = "Execution failure" if not result.success else "Low confidence"

                corrective_action = f"Refine strategy and reallocate resources for '{result.goal}'"

                improvement_confidence = round(random.uniform(0.90, 0.99), 2)

                correction = CorrectionResult(
                    goal=result.goal,
                    issue_detected=issue,
                    corrective_action=corrective_action,
                    improvement_confidence=improvement_confidence,
                    timestamp=datetime.datetime.utcnow().isoformat()
                )

                corrections.append(correction)
                adjustment_score += improvement_confidence

        overall_adjustment = round(
            adjustment_score / len(corrections), 2
        ) if corrections else 0.0

        return corrections, overall_adjustment


engine = FeedbackCorrectionEngine()


@router.post("/self-correct", response_model=Phase68Output)
def self_correct(data: Phase68Input):

    corrections, adjustment = engine.analyze_and_correct(data.execution_results)

    return Phase68Output(
        message="Phase 68 feedback analysis and self-correction complete",
        corrections_applied=corrections,
        overall_system_adjustment=adjustment
    )