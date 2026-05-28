from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase102", tags=["Phase 102 — Self-Directed Evolution & Cross-Domain Innovation"])

# ---------------------------
# Input Models
# ---------------------------
class NodeEvolutionData(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    recent_success_rate: float
    past_modules: List[str]

class Phase102Input(BaseModel):
    global_goal: str
    nodes_data: List[NodeEvolutionData]

# ---------------------------
# Output Models
# ---------------------------
class EvolutionOutcome(BaseModel):
    instance_id: str
    enterprise_id: str
    node_id: str
    system_name: str
    new_module_generated: str
    experiment_result: str
    predicted_success: float
    timestamp: str

class Phase102Output(BaseModel):
    message: str
    global_goal: str
    evolution_outcomes: List[EvolutionOutcome]
    overall_evolution_score: float
    timestamp: str

# ---------------------------
# Engine Class
# ---------------------------
class SelfDirectedEvolutionEngine:

    def evolve(self, nodes_data: List[NodeEvolutionData]):
        outcomes = []
        total_score = 0

        for node in nodes_data:
            # Generate new cross-domain module
            if node.recent_success_rate < 0.8:
                new_module = "Cross-Domain Optimization Module"
                experiment_result = random.choice(["Success", "Partial Success", "Requires Adjustment"])
                predicted_success = round(random.uniform(0.7, 0.92), 3)
            else:
                new_module = "Minor Efficiency Patch"
                experiment_result = "Success"
                predicted_success = round(random.uniform(0.85, 0.99), 3)

            outcomes.append(EvolutionOutcome(
                instance_id=node.instance_id,
                enterprise_id=node.enterprise_id,
                node_id=node.node_id,
                system_name=node.system_name,
                new_module_generated=new_module,
                experiment_result=experiment_result,
                predicted_success=predicted_success,
                timestamp=str(datetime.datetime.now())
            ))

            total_score += predicted_success

        overall_score = round(total_score / len(nodes_data), 3) if nodes_data else 0

        return outcomes, overall_score

engine = SelfDirectedEvolutionEngine()

# ---------------------------
# API Endpoint
# ---------------------------
@router.post("/evolve", response_model=Phase102Output)
def self_directed_evolution(data: Phase102Input):
    outcomes, overall_score = engine.evolve(data.nodes_data)

    return Phase102Output(
        message=f"Phase 102 self-directed evolution complete for goal '{data.global_goal}'",
        global_goal=data.global_goal,
        evolution_outcomes=outcomes,
        overall_evolution_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )