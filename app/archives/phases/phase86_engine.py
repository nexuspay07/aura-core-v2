from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(prefix="/phase86", tags=["Phase 86 — Global Optimization Engine"])


# INPUT
class ResourceSystem(BaseModel):
    system_name: str
    efficiency_score: float   # 0–1
    demand_level: float       # 0–1
    risk_level: float         # 0–1


class Phase86Input(BaseModel):
    total_resources: float
    systems: List[ResourceSystem]


# OUTPUT
class AllocationResult(BaseModel):
    system_name: str
    allocated_resources: float
    expected_improvement: float


class Phase86Output(BaseModel):
    message: str
    allocation_results: List[AllocationResult]
    global_efficiency_gain: float
    timestamp: str


class GlobalOptimizationEngine:

    def optimize(self, total_resources, systems):

        priority_scores = []

        for system in systems:

            priority = (
                (1 - system.efficiency_score) * 0.5 +
                system.demand_level * 0.3 +
                system.risk_level * 0.2
            )

            priority_scores.append({
                "system": system,
                "priority": priority
            })

        total_priority = sum(p["priority"] for p in priority_scores)

        results = []
        total_improvement = 0

        for item in priority_scores:

            system = item["system"]
            priority = item["priority"]

            if total_priority == 0:
                allocated = 0
            else:
                allocated = (priority / total_priority) * total_resources

            expected_improvement = round(allocated * 0.05, 3)

            total_improvement += expected_improvement

            results.append(
                AllocationResult(
                    system_name=system.system_name,
                    allocated_resources=round(allocated, 3),
                    expected_improvement=expected_improvement
                )
            )

        global_gain = round(total_improvement, 3)

        return results, global_gain


engine = GlobalOptimizationEngine()


@router.post("/optimize-resources", response_model=Phase86Output)
def optimize_resources(data: Phase86Input):

    results, gain = engine.optimize(
        data.total_resources,
        data.systems
    )

    return Phase86Output(
        message="Phase 86 global optimization complete",
        allocation_results=results,
        global_efficiency_gain=gain,
        timestamp=str(datetime.datetime.now())
    )