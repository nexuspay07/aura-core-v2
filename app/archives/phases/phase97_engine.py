from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase97", tags=["Phase 97 — Adaptive Multi-Enterprise Orchestration"])

# INPUT
class EnterpriseNode(BaseModel):
    enterprise_id: str
    node_id: str
    system_name: str
    action: str
    priority: str  # high, medium, low
    recent_success_rate: float

class Phase97Input(BaseModel):
    goal: str
    enterprise_nodes: List[EnterpriseNode]

# OUTPUT
class AdaptiveOutcome(BaseModel):
    enterprise_id: str
    node_id: str
    system_name: str
    action_executed: bool
    adjusted_priority: str
    predicted_success: float
    timestamp: str

class Phase97Output(BaseModel):
    message: str
    goal: str
    outcomes: List[AdaptiveOutcome]
    overall_adaptive_score: float
    timestamp: str

# ENGINE
class AdaptiveOrchestrationEngine:

    def adapt(self, enterprise_nodes: List[EnterpriseNode]):
        outcomes = []
        total_score = 0

        for node in enterprise_nodes:
            # Adaptive adjustment
            if node.recent_success_rate < 0.8:
                adjusted_priority = "high"
                executed = True
                predicted_success = round(random.uniform(0.75, 0.9), 3)
            else:
                adjusted_priority = node.priority
                executed = True
                predicted_success = round(random.uniform(0.85, 1.0), 3)

            outcomes.append(AdaptiveOutcome(
                enterprise_id=node.enterprise_id,
                node_id=node.node_id,
                system_name=node.system_name,
                action_executed=executed,
                adjusted_priority=adjusted_priority,
                predicted_success=predicted_success,
                timestamp=str(datetime.datetime.now())
            ))

            total_score += predicted_success

        overall_score = round(total_score / len(enterprise_nodes), 3) if enterprise_nodes else 0

        return outcomes, overall_score

engine = AdaptiveOrchestrationEngine()

@router.post("/adapt", response_model=Phase97Output)
def adaptive_orchestration(data: Phase97Input):
    outcomes, overall_score = engine.adapt(data.enterprise_nodes)

    return Phase97Output(
        message=f"Phase 97 adaptive multi-enterprise orchestration complete for goal '{data.goal}'",
        goal=data.goal,
        outcomes=outcomes,
        overall_adaptive_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )