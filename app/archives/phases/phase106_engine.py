from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase106",
    tags=["Phase 106 — Adaptive Real-Time Learning Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class StepExecutionResultInput(BaseModel):
    step_id: str
    action: str
    execution_status: str
    actual_success_probability: float


class PlanExecutionReportInput(BaseModel):
    plan_id: str
    enterprise_id: str
    system_name: str
    steps_results: List[StepExecutionResultInput]
    final_status: str


class Phase106Input(BaseModel):
    global_mission: str
    execution_reports: List[PlanExecutionReportInput]


# ---------------------------
# Output Models
# ---------------------------

class AdaptiveInsight(BaseModel):
    enterprise_id: str
    system_name: str
    success_rate: float
    detected_risk_level: float
    recommended_adjustment: str


class Phase106Output(BaseModel):
    message: str
    adaptive_insights: List[AdaptiveInsight]
    global_adaptive_score: float
    timestamp: str


# ---------------------------
# Learning Engine
# ---------------------------

class AdaptiveLearningEngine:

    def analyze_report(self, report: PlanExecutionReportInput):

        total_steps = len(report.steps_results)
        success_count = 0
        total_probability = 0

        for step in report.steps_results:
            total_probability += step.actual_success_probability
            if step.execution_status == "SUCCESS":
                success_count += 1

        success_rate = success_count / total_steps if total_steps else 0
        avg_probability = total_probability / total_steps if total_steps else 0

        # Risk increases if success rate drops
        detected_risk = round(1 - success_rate, 3)

        if detected_risk > 0.3:
            adjustment = "Increase monitoring and refine optimization algorithms"
        else:
            adjustment = "Maintain current adaptive strategy"

        return AdaptiveInsight(
            enterprise_id=report.enterprise_id,
            system_name=report.system_name,
            success_rate=round(success_rate, 3),
            detected_risk_level=detected_risk,
            recommended_adjustment=adjustment
        )


    def run_adaptive_learning(self, reports: List[PlanExecutionReportInput]):

        insights = []
        total_score = 0

        for report in reports:
            insight = self.analyze_report(report)
            insights.append(insight)
            total_score += insight.success_rate

        global_score = total_score / len(insights) if insights else 0

        return insights, round(global_score, 3)


engine = AdaptiveLearningEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/learn", response_model=Phase106Output)
def adaptive_learning(data: Phase106Input):

    insights, global_score = engine.run_adaptive_learning(data.execution_reports)

    return Phase106Output(
        message="Phase 106 adaptive learning complete",
        adaptive_insights=insights,
        global_adaptive_score=global_score,
        timestamp=str(datetime.datetime.now())
    )