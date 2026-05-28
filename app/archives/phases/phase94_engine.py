from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase94", tags=["Phase 94 — Fault-Tolerant Deployment"])

# INPUT
class NodeHealth(BaseModel):
    node_id: str
    online: bool
    system_load: float  # 0 to 1
    critical_tasks: int

class Phase94Input(BaseModel):
    nodes: List[NodeHealth]
    enterprise_goal: str

# OUTPUT
class NodeStatus(BaseModel):
    node_id: str
    action_taken: str
    rerouted: bool
    success_rate: float
    timestamp: str

class Phase94Output(BaseModel):
    message: str
    enterprise_goal: str
    node_statuses: List[NodeStatus]
    network_resilience_score: float
    timestamp: str

# ENGINE
class FaultTolerantEngine:

    def deploy(self, nodes: List[NodeHealth], goal: str):
        statuses = []
        total_score = 0

        for node in nodes:

            if not node.online:
                rerouted = True
                action_taken = "Tasks rerouted to backup node"
                success_rate = round(random.uniform(0.7, 0.95), 3)
            else:
                rerouted = False
                action_taken = "Executed tasks normally"
                success_rate = round(random.uniform(0.8, 1.0 - node.system_load*0.1), 3)

            statuses.append(NodeStatus(
                node_id=node.node_id,
                action_taken=action_taken,
                rerouted=rerouted,
                success_rate=success_rate,
                timestamp=str(datetime.datetime.now())
            ))

            total_score += success_rate

        resilience_score = round(total_score / len(nodes), 3) if nodes else 0

        return statuses, resilience_score

engine = FaultTolerantEngine()

@router.post("/deploy", response_model=Phase94Output)
def deploy_enterprise(data: Phase94Input):
    statuses, score = engine.deploy(data.nodes, data.enterprise_goal)

    return Phase94Output(
        message=f"Phase 94 fault-tolerant deployment complete for goal '{data.enterprise_goal}'",
        enterprise_goal=data.enterprise_goal,
        node_statuses=statuses,
        network_resilience_score=score,
        timestamp=str(datetime.datetime.now())
    )