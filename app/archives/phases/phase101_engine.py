from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase101", tags=["Phase 101 — Meta-Autonomous Capability Expansion"])

# ---------------------------
# Input Models
# ---------------------------
class NodeMetaPerformance(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    recent_success_rate: float
    past_strategies: List[str]

class Phase101Input(BaseModel):
    global_goal: str
    nodes_performance: List[NodeMetaPerformance]

# ---------------------------
# Output Models
# ---------------------------
class MetaImprovementOutcome(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    proposed_module: str
    experiment_result: str
    predicted_success: float
    timestamp: str

class Phase101Output(BaseModel):
    message: str
    global_goal: str
    meta_improvements: List[MetaImprovementOutcome]
    overall_meta_score: float
    timestamp: str

# ---------------------------
# Engine Class
# ---------------------------
class MetaAutonomousEngine:

    def expand_capabilities(self, nodes_performance: List[NodeMetaPerformance]):
        meta_improvements = []
        total_score = 0

        for node in nodes_performance:
            # Generate new meta-module or strategy
            if node.recent_success_rate < 0.8:
                proposed_module = "Adaptive Resource Rebalancing Module"
                experiment_result = random.choice(["Success", "Partial Success", "Requires Adjustment"])
                predicted_success = round(random.uniform(0.75, 0.92), 3)
            else:
                proposed_module = "Minor Optimization Patch"
                experiment_result = "Success"
                predicted_success = round(random.uniform(0.85, 0.99), 3)

            meta_improvements.append(MetaImprovementOutcome(
                instance_id=node.instance_id,
                enterprise_id=node.enterprise_id,
                node_id=node.node_id,
                system_name=node.system_name,
                proposed_module=proposed_module,
                experiment_result=experiment_result,
                predicted_success=predicted_success,
                timestamp=str(datetime.datetime.now())
            ))

            total_score += predicted_success

        overall_meta_score = round(total_score / len(nodes_performance), 3) if nodes_performance else 0

        return meta_improvements, overall_meta_score


engine = MetaAutonomousEngine()

# ---------------------------
# API Endpoint
# ---------------------------
@router.post("/meta-expand", response_model=Phase101Output)
def meta_autonomous_expansion(data: Phase101Input):
    improvements, overall_score = engine.expand_capabilities(data.nodes_performance)

    return Phase101Output(
        message=f"Phase 101 meta-autonomous capability expansion complete for goal '{data.global_goal}'",
        global_goal=data.global_goal,
        meta_improvements=improvements,
        overall_meta_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )