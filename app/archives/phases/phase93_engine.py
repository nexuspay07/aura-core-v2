from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase93", tags=["Phase 93 — Enterprise Orchestration Engine"])


# INPUT
class NodeAction(BaseModel):
    node_id: str
    system_name: str
    action: str
    priority: str  # high, medium, low
    governance_approved: bool


class Phase93Input(BaseModel):
    enterprise_goal: str
    node_actions: List[NodeAction]


# OUTPUT
class NodeExecutionResult(BaseModel):
    node_id: str
    system_name: str
    action: str
    executed: bool
    success_rate: float
    anomaly_detected: bool
    timestamp: str


class Phase93Output(BaseModel):
    message: str
    enterprise_goal: str
    execution_results: List[NodeExecutionResult]
    enterprise_success_score: float
    total_nodes: int
    timestamp: str


# ENGINE
class EnterpriseOrchestrationEngine:

    def orchestrate(self, node_actions: List[NodeAction]):

        results = []
        total_success = 0
        count = 0
        nodes_set = set()

        for act in node_actions:

            nodes_set.add(act.node_id)

            if not act.governance_approved:
                executed = False
                success_rate = 0.0
                anomaly = False
            else:
                # High priority actions more likely to succeed
                base = 0.7 if act.priority == "high" else 0.6
                success_rate = round(random.uniform(base, 1.0), 3)
                anomaly = success_rate < 0.75
                executed = True

            results.append(NodeExecutionResult(
                node_id=act.node_id,
                system_name=act.system_name,
                action=act.action,
                executed=executed,
                success_rate=success_rate,
                anomaly_detected=anomaly,
                timestamp=str(datetime.datetime.now())
            ))

            if executed:
                total_success += success_rate
                count += 1

        enterprise_score = round(total_success / count, 3) if count > 0 else 0.0

        return results, enterprise_score, len(nodes_set)


engine = EnterpriseOrchestrationEngine()


@router.post("/orchestrate", response_model=Phase93Output)
def orchestrate_actions(data: Phase93Input):

    results, score, total_nodes = engine.orchestrate(data.node_actions)

    return Phase93Output(
        message="Phase 93 enterprise orchestration complete",
        enterprise_goal=data.enterprise_goal,
        execution_results=results,
        enterprise_success_score=score,
        total_nodes=total_nodes,
        timestamp=str(datetime.datetime.now())
    )