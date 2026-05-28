from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import datetime

router = APIRouter(prefix="/phase83", tags=["Phase 83 — Natural Collaboration Layer"])


# INPUT
class CollaborationInput(BaseModel):
    decision: str
    confidence: float
    governance_score: float
    human_feedback: Optional[str] = None


# OUTPUT
class Phase83Output(BaseModel):
    message: str
    explanation: str
    adjusted_decision: str
    collaboration_status: str
    timestamp: str


class CollaborationEngine:

    def collaborate(self, decision, confidence, governance_score, human_feedback):

        explanation = (
            f"The decision '{decision}' was selected because it "
            f"achieved a confidence score of {confidence} "
            f"and a governance compliance score of {governance_score}. "
        )

        adjusted_decision = decision
        collaboration_status = "Decision confirmed"

        # Simple human feedback handling
        if human_feedback:
            if "reject" in human_feedback.lower():
                adjusted_decision = "Decision requires reevaluation"
                collaboration_status = "Human override applied"
            elif "modify" in human_feedback.lower():
                adjusted_decision = f"Modified based on feedback: {decision}"
                collaboration_status = "Decision modified collaboratively"

        return explanation, adjusted_decision, collaboration_status


engine = CollaborationEngine()


@router.post("/collaborate", response_model=Phase83Output)
def collaborate(data: CollaborationInput):

    explanation, adjusted, status = engine.collaborate(
        data.decision,
        data.confidence,
        data.governance_score,
        data.human_feedback
    )

    return Phase83Output(
        message="Phase 83 collaboration process complete",
        explanation=explanation,
        adjusted_decision=adjusted,
        collaboration_status=status,
        timestamp=str(datetime.datetime.now())
    )