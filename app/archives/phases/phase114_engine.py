from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import datetime

router = APIRouter(
    prefix="/phase114",
    tags=["Phase 114 — Autonomous Risk Mitigation Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class RiskInput(BaseModel):
    system_name: str
    predicted_issue: str
    confidence_score: float

class Phase114Input(BaseModel):
    global_mission: str
    predicted_risks: List[RiskInput]


# ---------------------------
# Output Models
# ---------------------------

class MitigationPlan(BaseModel):
    system_name: str
    risk_level: str
    contingency_action: str
    expected_outcome: str
    mitigation_confidence: float

class Phase114Output(BaseModel):
    message: str
    mitigation_plans: List[MitigationPlan]
    overall_mitigation_efficiency: float
    timestamp: str


# ---------------------------
# Risk Mitigation Engine
# ---------------------------

class RiskMitigationEngine:

    def create_plan(self, risk: RiskInput):
        confidence = risk.confidence_score

        if confidence > 0.7:
            risk_level = "High"
            action = "Scale resources, redistribute tasks, alert admins"
            outcome = "Issue likely prevented"
        elif confidence > 0.4:
            risk_level = "Medium"
            action = "Optimize workflow and monitor system closely"
            outcome = "Issue risk reduced"
        else:
            risk_level = "Low"
            action = "Monitor system"
            outcome = "Minimal action required"

        mitigation_confidence = round(confidence + 0.2, 3)  # improves confidence slightly

        return MitigationPlan(
            system_name=risk.system_name,
            risk_level=risk_level,
            contingency_action=action,
            expected_outcome=outcome,
            mitigation_confidence=mitigation_confidence
        )

    def run_mitigation(self, predicted_risks: List[RiskInput]):
        plans = []
        total_confidence = 0
        count = 0

        for risk in predicted_risks:
            plan = self.create_plan(risk)
            plans.append(plan)
            total_confidence += plan.mitigation_confidence
            count += 1

        overall_efficiency = round(total_confidence / count if count else 0, 3)
        return plans, overall_efficiency


engine = RiskMitigationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/mitigate", response_model=Phase114Output)
def mitigate_risks(data: Phase114Input):
    plans, efficiency = engine.run_mitigation(data.predicted_risks)

    return Phase114Output(
        message="Phase 114 risk mitigation planning complete",
        mitigation_plans=plans,
        overall_mitigation_efficiency=efficiency,
        timestamp=str(datetime.datetime.now())
    )