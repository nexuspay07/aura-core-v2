from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase115",
    tags=["Phase 115 — Autonomous Self-Optimization Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemPerformance(BaseModel):
    system_name: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    efficiency_score: float

class Phase115Input(BaseModel):
    global_mission: str
    systems_performance: List[SystemPerformance]


# ---------------------------
# Output Models
# ---------------------------

class OptimizationResult(BaseModel):
    system_name: str
    action_taken: str
    new_efficiency_score: float

class Phase115Output(BaseModel):
    message: str
    optimization_results: List[OptimizationResult]
    overall_optimization_score: float
    timestamp: str


# ---------------------------
# Self-Optimization Engine
# ---------------------------

class SelfOptimizationEngine:

    def optimize_system(self, system: SystemPerformance):
        # Simulate optimization by reducing load and increasing efficiency
        load_factor = (system.cpu_usage + system.memory_usage) / 2
        improvement = 0.1 * (1 - load_factor)  # increase efficiency slightly
        new_efficiency = min(system.efficiency_score + improvement, 1.0)
        
        return OptimizationResult(
            system_name=system.system_name,
            action_taken="Resources optimized, tasks rebalanced",
            new_efficiency_score=round(new_efficiency, 3)
        )

    def optimize_all(self, systems: List[SystemPerformance]):
        results = []
        total_score = 0
        for system in systems:
            result = self.optimize_system(system)
            results.append(result)
            total_score += result.new_efficiency_score
        overall_score = round(total_score / len(systems) if systems else 0, 3)
        return results, overall_score


engine = SelfOptimizationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/optimize", response_model=Phase115Output)
def self_optimize(data: Phase115Input):
    results, overall_score = engine.optimize_all(data.systems_performance)

    return Phase115Output(
        message="Phase 115 self-optimization complete",
        optimization_results=results,
        overall_optimization_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )