from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase95", tags=["Phase 95 — Enterprise Self-Optimization"])

# INPUT
class NodePerformance(BaseModel):
    node_id: str
    success_rate: float
    system_load: float
    critical_tasks: int

class Phase95Input(BaseModel):
    enterprise_goal: str
    node_performance: List[NodePerformance]

# OUTPUT
class OptimizationResult(BaseModel):
    node_id: str
    recommended_action: str
    new_priority: str
    predicted_success_improvement: float

class Phase95Output(BaseModel):
    message: str
    enterprise_goal: str
    optimization_results: List[OptimizationResult]
    overall_expected_success: float
    timestamp: str

# ENGINE
class EnterpriseSelfOptimizationEngine:

    def optimize(self, node_perf: List[NodePerformance]):

        results = []
        total_expected = 0

        for node in node_perf:

            # Adjust priority based on load and success rate
            if node.success_rate < 0.8:
                new_priority = "high"
                recommended_action = "Increase resources / redistribute tasks"
                improvement = round(random.uniform(0.05, 0.15), 3)
            else:
                new_priority = "medium"
                recommended_action = "Maintain current strategy"
                improvement = round(random.uniform(0.01, 0.05), 3)

            results.append(OptimizationResult(
                node_id=node.node_id,
                recommended_action=recommended_action,
                new_priority=new_priority,
                predicted_success_improvement=improvement
            ))

            total_expected += node.success_rate + improvement

        overall_expected = round(total_expected / len(node_perf), 3) if node_perf else 0

        return results, overall_expected

engine = EnterpriseSelfOptimizationEngine()

@router.post("/optimize", response_model=Phase95Output)
def optimize_enterprise(data: Phase95Input):

    results, overall_expected = engine.optimize(data.node_performance)

    return Phase95Output(
        message=f"Phase 95 enterprise self-optimization complete for goal '{data.enterprise_goal}'",
        enterprise_goal=data.enterprise_goal,
        optimization_results=results,
        overall_expected_success=overall_expected,
        timestamp=str(datetime.datetime.now())
    )