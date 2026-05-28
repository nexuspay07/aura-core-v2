from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import datetime
import random

router = APIRouter(prefix="/phase80", tags=["Phase 80 — Global Autonomous Decision Network"])

# INPUT
class NodeResult(BaseModel):
    node_id: str
    goal: str
    prediction: float  # Confidence of success
    recommended_action: str

class Phase80Input(BaseModel):
    goal: str
    node_results: List[NodeResult]

# OUTPUT
class DecisionResult(BaseModel):
    action: str
    aggregated_confidence: float
    approved: bool

class Phase80Output(BaseModel):
    message: str
    global_decision: DecisionResult
    timestamp: str

# Engine
class GlobalDecisionEngine:

    def make_decision(self, goal: str, node_results: List[NodeResult]) -> DecisionResult:
        if not node_results:
            return DecisionResult(
                action="No decision possible",
                aggregated_confidence=0.0,
                approved=False
            )

        # Aggregate predictions from nodes
        avg_confidence = round(
            sum([nr.prediction for nr in node_results]) / len(node_results), 3
        )

        # Choose the action with highest confidence from nodes
        recommended_actions = [nr.recommended_action for nr in node_results]
        # For simplicity, pick the first action among top confidence nodes
        top_confidence = max([nr.prediction for nr in node_results])
        top_actions = [nr.recommended_action for nr in node_results if nr.prediction == top_confidence]
        final_action = top_actions[0] if top_actions else recommended_actions[0]

        approved = avg_confidence >= 0.7

        return DecisionResult(
            action=final_action,
            aggregated_confidence=avg_confidence,
            approved=approved
        )

engine = GlobalDecisionEngine()

@router.post("/global-decide", response_model=Phase80Output)
def global_decide(data: Phase80Input):
    decision = engine.make_decision(data.goal, data.node_results)
    return Phase80Output(
        message=f"Phase 80 global decision complete for goal '{data.goal}'",
        global_decision=decision,
        timestamp=str(datetime.datetime.now())
    )