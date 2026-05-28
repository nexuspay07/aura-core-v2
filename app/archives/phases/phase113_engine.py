from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(
    prefix="/phase113",
    tags=["Phase 113 — Autonomous Predictive Decision-Making Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemMetrics(BaseModel):
    system_name: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    historical_failure_rate: float

class Phase113Input(BaseModel):
    global_mission: str
    systems_metrics: List[SystemMetrics]


# ---------------------------
# Output Models
# ---------------------------

class PredictiveDecision(BaseModel):
    system_name: str
    predicted_issue: str
    preventive_action: str
    confidence_score: float

class Phase113Output(BaseModel):
    message: str
    predictive_decisions: List[PredictiveDecision]
    overall_decision_confidence: float
    timestamp: str


# ---------------------------
# Predictive Engine
# ---------------------------

class PredictiveDecisionEngine:

    def analyze_system(self, metrics: SystemMetrics):
        # Simple predictive logic
        issue_risk = (metrics.cpu_usage + metrics.memory_usage) / 2 + metrics.historical_failure_rate
        confidence = round(random.uniform(0.7, 0.99) * (1 - issue_risk), 3)
        
        if issue_risk > 1.2:
            predicted_issue = "High risk of failure"
            preventive_action = "Scale resources and redistribute tasks"
        elif issue_risk > 0.8:
            predicted_issue = "Medium risk of slowdown"
            preventive_action = "Optimize task allocation"
        else:
            predicted_issue = "Low risk"
            preventive_action = "Monitor system"

        return PredictiveDecision(
            system_name=metrics.system_name,
            predicted_issue=predicted_issue,
            preventive_action=preventive_action,
            confidence_score=confidence
        )

    def make_predictions(self, metrics_list: List[SystemMetrics]):
        decisions = []
        total_confidence = 0
        for metrics in metrics_list:
            decision = self.analyze_system(metrics)
            decisions.append(decision)
            total_confidence += decision.confidence_score
        overall_confidence = round(total_confidence / len(metrics_list), 3) if metrics_list else 0
        return decisions, overall_confidence


engine = PredictiveDecisionEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/predict", response_model=Phase113Output)
def predictive_decision(data: Phase113Input):
    decisions, overall_confidence = engine.make_predictions(data.systems_metrics)

    return Phase113Output(
        message="Phase 113 predictive decision-making complete",
        predictive_decisions=decisions,
        overall_decision_confidence=overall_confidence,
        timestamp=str(datetime.datetime.now())
    )