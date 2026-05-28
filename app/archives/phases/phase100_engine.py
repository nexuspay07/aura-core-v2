from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase100", tags=["Phase 100 — Global Multi-Instance Intelligence"])

# INPUT
class GlobalNode(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    action: str
    priority: str  # high, medium, low
    recent_success_rate: float
    critical_tasks: int

class Phase100Input(BaseModel):
    global_goal: str
    global_nodes: List[GlobalNode]

# OUTPUT
class NodeGlobalOutcome(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    action_executed: bool
    adjusted_priority: str
    predicted_success: float
    auto_improvement_applied: bool
    timestamp: str

class Phase100Output(BaseModel):
    message: str
    global_goal: str
    node_outcomes: List[NodeGlobalOutcome]
    overall_global_score: float
    timestamp: str

# ENGINE
class GlobalMultiInstanceEngine:

    def execute_global(self, global_nodes: List[GlobalNode]):
        outcomes = []
        total_score = 0

        for node in global_nodes:
            # Autonomous global adjustment
            if node.recent_success_rate < 0.8 or node.critical_tasks > 3:
                adjusted_priority = "high"
                executed = True
                auto_improvement = True
                predicted_success = round(random.uniform(0.75, 0.93), 3)
            else:
                adjusted_priority = node.priority
                executed = True
                auto_improvement = False
                predicted_success = round(random.uniform(0.85, 0.99), 3)

            outcomes.append(NodeGlobalOutcome(
                instance_id=node.instance_id,
                enterprise_id=node.enterprise_id,
                node_id=node.node_id,
                system_name=node.system_name,
                action_executed=executed,
                adjusted_priority=adjusted_priority,
                predicted_success=predicted_success,
                auto_improvement_applied=auto_improvement,
                timestamp=str(datetime.datetime.now())
            ))

            total_score += predicted_success

        overall_global_score = round(total_score / len(global_nodes), 3) if global_nodes else 0

        return outcomes, overall_global_score

engine = GlobalMultiInstanceEngine()

@router.post("/execute", response_model=Phase100Output)
def global_execution(data: Phase100Input):
    outcomes, overall_score = engine.execute_global(data.global_nodes)

    return Phase100Output(
        message=f"Phase 100 global multi-instance execution complete for goal '{data.global_goal}'",
        global_goal=data.global_goal,
        node_outcomes=outcomes,
        overall_global_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )