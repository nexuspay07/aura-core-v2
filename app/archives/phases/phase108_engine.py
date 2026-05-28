from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase108",
    tags=["Phase 108 — Autonomous System Self-Optimization Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemPerformanceInput(BaseModel):
    system_name: str
    execution_success_rate: float
    average_execution_time: float
    failure_rate: float
    resource_efficiency: float


class Phase108Input(BaseModel):
    global_mission: str
    system_performances: List[SystemPerformanceInput]


# ---------------------------
# Output Models
# ---------------------------

class OptimizationResult(BaseModel):
    system_name: str
    optimization_applied: str
    performance_improvement: float
    new_expected_success_rate: float


class Phase108Output(BaseModel):
    message: str
    optimization_results: List[OptimizationResult]
    global_system_efficiency_score: float
    timestamp: str


# ---------------------------
# Self Optimization Engine
# ---------------------------

class SelfOptimizationEngine:

    def optimize_system(self, system: SystemPerformanceInput):

        improvement = round((1 - system.failure_rate) * 0.05, 3)

        new_success_rate = system.execution_success_rate + improvement

        if new_success_rate > 1:
            new_success_rate = 1.0

        if system.failure_rate > 0.3:
            optimization = "Applied failure reduction optimization"
        elif system.resource_efficiency < 0.7:
            optimization = "Applied resource efficiency optimization"
        else:
            optimization = "Applied performance fine-tuning"

        return OptimizationResult(
            system_name=system.system_name,
            optimization_applied=optimization,
            performance_improvement=improvement,
            new_expected_success_rate=round(new_success_rate, 3)
        )


    def optimize_all(self, systems: List[SystemPerformanceInput]):

        results = []
        total_efficiency = 0

        for system in systems:

            result = self.optimize_system(system)

            results.append(result)

            total_efficiency += result.new_expected_success_rate

        global_score = total_efficiency / len(systems) if systems else 0

        return results, round(global_score, 3)


engine = SelfOptimizationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/self-optimize", response_model=Phase108Output)
def self_optimize(data: Phase108Input):

    results, global_score = engine.optimize_all(data.system_performances)

    return Phase108Output(
        message="Phase 108 autonomous self-optimization complete",
        optimization_results=results,
        global_system_efficiency_score=global_score,
        timestamp=str(datetime.datetime.now())
    )