from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase96", tags=["Phase 96 — Predictive Orchestration Engine"])

# INPUT
class NodeFutureAction(BaseModel):
    node_id: str
    system_name: str
    action: str
    priority: str  # high, medium, low

class Phase96Input(BaseModel):
    enterprise_goal: str
    future_actions: List[NodeFutureAction]

# OUTPUT
class PredictedOutcome(BaseModel):
    node_id: str
    system_name: str
    action: str
    predicted_success: float
    recommended_adjustment: str

class Phase96Output(BaseModel):
    message: str
    enterprise_goal: str
    predictions: List[PredictedOutcome]
    overall_predicted_success: float
    timestamp: str

# ENGINE
class PredictiveOrchestrationEngine:

    def predict(self, future_actions: List[NodeFutureAction]):
        predictions = []
        total_predicted = 0

        for act in future_actions:
            base = 0.8 if act.priority == "high" else 0.7
            predicted_success = round(random.uniform(base, 1.0), 3)
            recommended_adjustment = "Increase resources" if predicted_success < 0.85 else "Maintain plan"

            predictions.append(PredictedOutcome(
                node_id=act.node_id,
                system_name=act.system_name,
                action=act.action,
                predicted_success=predicted_success,
                recommended_adjustment=recommended_adjustment
            ))

            total_predicted += predicted_success

        overall_predicted = round(total_predicted / len(future_actions), 3) if future_actions else 0.0

        return predictions, overall_predicted

engine = PredictiveOrchestrationEngine()

@router.post("/predict", response_model=Phase96Output)
def predictive_orchestration(data: Phase96Input):
    predictions, overall_predicted = engine.predict(data.future_actions)

    return Phase96Output(
        message=f"Phase 96 predictive orchestration complete for goal '{data.enterprise_goal}'",
        enterprise_goal=data.enterprise_goal,
        predictions=predictions,
        overall_predicted_success=overall_predicted,
        timestamp=str(datetime.datetime.now())
    )