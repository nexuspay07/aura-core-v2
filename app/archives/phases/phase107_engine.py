from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase107",
    tags=["Phase 107 — Predictive Pre-Execution Risk Prevention Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class ExecutionStepInput(BaseModel):
    step_id: str
    action: str
    priority: str
    estimated_success_probability: float


class ExecutionPlanInput(BaseModel):
    plan_id: str
    enterprise_id: str
    system_name: str
    steps: List[ExecutionStepInput]
    overall_success_probability: float


class Phase107Input(BaseModel):
    global_mission: str
    execution_plans: List[ExecutionPlanInput]


# ---------------------------
# Output Models
# ---------------------------

class RiskAssessment(BaseModel):
    plan_id: str
    enterprise_id: str
    system_name: str
    predicted_failure_risk: float
    prevention_recommendation: str
    execution_safety_status: str


class Phase107Output(BaseModel):
    message: str
    risk_assessments: List[RiskAssessment]
    global_execution_safety_score: float
    timestamp: str


# ---------------------------
# Risk Prevention Engine
# ---------------------------

class PredictiveRiskPreventionEngine:

    def analyze_plan(self, plan: ExecutionPlanInput):

        risk = round(1 - plan.overall_success_probability, 3)

        if risk > 0.4:
            recommendation = "BLOCK execution and redesign execution plan"
            status = "UNSAFE"

        elif risk > 0.2:
            recommendation = "Allow execution with enhanced monitoring"
            status = "CAUTION"

        else:
            recommendation = "Execution safe to proceed"
            status = "SAFE"

        return RiskAssessment(
            plan_id=plan.plan_id,
            enterprise_id=plan.enterprise_id,
            system_name=plan.system_name,
            predicted_failure_risk=risk,
            prevention_recommendation=recommendation,
            execution_safety_status=status
        )


    def evaluate_all(self, plans: List[ExecutionPlanInput]):

        assessments = []
        total_safety = 0

        for plan in plans:

            assessment = self.analyze_plan(plan)
            assessments.append(assessment)

            safety_score = 1 - assessment.predicted_failure_risk
            total_safety += safety_score

        global_score = total_safety / len(plans) if plans else 0

        return assessments, round(global_score, 3)


engine = PredictiveRiskPreventionEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/prevent-risk", response_model=Phase107Output)
def prevent_execution_risk(data: Phase107Input):

    assessments, global_score = engine.evaluate_all(data.execution_plans)

    return Phase107Output(
        message="Phase 107 predictive risk prevention complete",
        risk_assessments=assessments,
        global_execution_safety_score=global_score,
        timestamp=str(datetime.datetime.now())
    )