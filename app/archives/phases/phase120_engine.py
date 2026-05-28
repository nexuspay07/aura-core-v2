from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(
    prefix="/phase120",
    tags=["Phase 120 — Autonomous Continuous Learning & Adaptation Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class DeployedSystem(BaseModel):
    domain_name: str
    system_name: str
    performance_score: float
    efficiency_score: float
    deployment_confidence: float

class Phase120Input(BaseModel):
    global_mission: str
    deployed_systems: List[DeployedSystem]


# ---------------------------
# Output Models
# ---------------------------

class AdaptationResult(BaseModel):
    domain_name: str
    system_name: str
    adaptation_action: str
    new_performance_score: float

class Phase120Output(BaseModel):
    message: str
    adaptation_results: List[AdaptationResult]
    overall_adaptation_score: float
    timestamp: str


# ---------------------------
# Continuous Learning Engine
# ---------------------------

class ContinuousLearningEngine:

    def adapt_system(self, system: DeployedSystem):
        # Simulate adaptation based on observed performance
        improvement = random.uniform(0.02, 0.1)
        new_score = min(system.performance_score + improvement, 1.0)
        action = "Optimized resources and updated workflow based on observations"

        return AdaptationResult(
            domain_name=system.domain_name,
            system_name=system.system_name,
            adaptation_action=action,
            new_performance_score=round(new_score, 3)
        )

    def adapt_all(self, systems: List[DeployedSystem]):
        results = []
        total_score = 0
        for system in systems:
            result = self.adapt_system(system)
            results.append(result)
            total_score += result.new_performance_score
        overall_score = round(total_score / len(systems) if systems else 0, 3)
        return results, overall_score


engine = ContinuousLearningEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/adapt", response_model=Phase120Output)
def continuous_adaptation(data: Phase120Input):
    results, overall_score = engine.adapt_all(data.deployed_systems)

    return Phase120Output(
        message="Phase 120 continuous learning & adaptation complete",
        adaptation_results=results,
        overall_adaptation_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )