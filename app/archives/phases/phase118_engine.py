from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase118",
    tags=["Phase 118 — Full-System Autonomy Evaluation Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemStatus(BaseModel):
    system_name: str
    efficiency_score: float
    knowledge_score: float
    innovation_score: float
    risk_mitigation_score: float

class Phase118Input(BaseModel):
    global_mission: str
    systems_status: List[SystemStatus]


# ---------------------------
# Output Models
# ---------------------------

class AutonomyEvaluation(BaseModel):
    system_name: str
    overall_readiness: float
    recommendations: str

class Phase118Output(BaseModel):
    message: str
    evaluations: List[AutonomyEvaluation]
    global_autonomy_score: float
    timestamp: str


# ---------------------------
# Autonomy Evaluation Engine
# ---------------------------

class AutonomyEvaluationEngine:

    def evaluate_system(self, status: SystemStatus):
        # Compute weighted overall readiness
        overall = round(
            0.3 * status.efficiency_score +
            0.3 * status.knowledge_score +
            0.3 * status.innovation_score +
            0.1 * status.risk_mitigation_score,
            3
        )

        recommendations = "System ready" if overall > 0.8 else "Further tuning required"

        return AutonomyEvaluation(
            system_name=status.system_name,
            overall_readiness=overall,
            recommendations=recommendations
        )

    def evaluate_all(self, systems: List[SystemStatus]):
        evaluations = []
        total_score = 0
        for status in systems:
            evaluation = self.evaluate_system(status)
            evaluations.append(evaluation)
            total_score += evaluation.overall_readiness
        global_score = round(total_score / len(systems) if systems else 0, 3)
        return evaluations, global_score


engine = AutonomyEvaluationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/evaluate", response_model=Phase118Output)
def evaluate_autonomy(data: Phase118Input):
    evaluations, global_score = engine.evaluate_all(data.systems_status)

    return Phase118Output(
        message="Phase 118 full-system autonomy evaluation complete",
        evaluations=evaluations,
        global_autonomy_score=global_score,
        timestamp=str(datetime.datetime.now())
    )