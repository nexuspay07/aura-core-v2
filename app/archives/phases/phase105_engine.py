from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(
    prefix="/phase105",
    tags=["Phase 105 — Controlled Autonomous Execution Engine"]
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


class Phase105Input(BaseModel):
    global_mission: str
    approval_token: str
    execution_plans: List[ExecutionPlanInput]


# ---------------------------
# Output Models
# ---------------------------

class StepExecutionResult(BaseModel):
    step_id: str
    action: str
    execution_status: str
    actual_success_probability: float


class PlanExecutionReport(BaseModel):
    plan_id: str
    enterprise_id: str
    system_name: str
    steps_results: List[StepExecutionResult]
    final_status: str


class Phase105Output(BaseModel):
    message: str
    execution_reports: List[PlanExecutionReport]
    global_execution_status: str
    timestamp: str


# ---------------------------
# Execution Engine
# ---------------------------

class ControlledExecutionEngine:

    SAFE_APPROVAL_TOKEN = "AURA_APPROVED"

    def execute_step(self, step: ExecutionStepInput):

        actual_success = round(
            step.estimated_success_probability * random.uniform(0.9, 1.05), 3
        )

        if actual_success < 0.7:
            status = "FAILED"
        else:
            status = "SUCCESS"

        return StepExecutionResult(
            step_id=step.step_id,
            action=step.action,
            execution_status=status,
            actual_success_probability=actual_success
        )


    def execute_plan(self, plan: ExecutionPlanInput):

        step_results = []
        failure_detected = False

        for step in plan.steps:
            result = self.execute_step(step)
            step_results.append(result)

            if result.execution_status == "FAILED":
                failure_detected = True

        final_status = "COMPLETED" if not failure_detected else "PARTIALLY_COMPLETED"

        return PlanExecutionReport(
            plan_id=plan.plan_id,
            enterprise_id=plan.enterprise_id,
            system_name=plan.system_name,
            steps_results=step_results,
            final_status=final_status
        )


    def execute_all(self, plans: List[ExecutionPlanInput]):

        reports = []
        overall_failure = False

        for plan in plans:
            report = self.execute_plan(plan)
            reports.append(report)

            if report.final_status != "COMPLETED":
                overall_failure = True

        global_status = "EXECUTION_COMPLETED" if not overall_failure else "EXECUTION_WITH_WARNINGS"

        return reports, global_status


engine = ControlledExecutionEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/execute", response_model=Phase105Output)
def execute_plans(data: Phase105Input):

    if data.approval_token != engine.SAFE_APPROVAL_TOKEN:
        return Phase105Output(
            message="Execution denied: invalid approval token",
            execution_reports=[],
            global_execution_status="DENIED",
            timestamp=str(datetime.datetime.now())
        )

    reports, global_status = engine.execute_all(data.execution_plans)

    return Phase105Output(
        message="Phase 105 controlled execution complete",
        execution_reports=reports,
        global_execution_status=global_status,
        timestamp=str(datetime.datetime.now())
    )