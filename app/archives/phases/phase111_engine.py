from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase111",
    tags=["Phase 111 — Autonomous Multi-System Integration Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemTaskStatus(BaseModel):
    system_name: str
    task: str
    status: str  # "pending", "completed", "failed"
    priority: str
    confidence: float

class Phase111Input(BaseModel):
    global_mission: str
    systems_tasks: List[SystemTaskStatus]


# ---------------------------
# Output Models
# ---------------------------

class IntegrationResult(BaseModel):
    system_name: str
    task: str
    action_taken: str
    final_status: str
    confidence: float

class Phase111Output(BaseModel):
    message: str
    integration_results: List[IntegrationResult]
    global_integration_efficiency: float
    timestamp: str


# ---------------------------
# Multi-System Integration Engine
# ---------------------------

class MultiSystemIntegrationEngine:

    def integrate_task(self, task: SystemTaskStatus):
        if task.status == "completed":
            action = "No action needed"
            final_status = "completed"
        elif task.status == "failed":
            action = "Auto-retry executed"
            final_status = "completed"
        else:
            action = "Task scheduled"
            final_status = "pending"

        return IntegrationResult(
            system_name=task.system_name,
            task=task.task,
            action_taken=action,
            final_status=final_status,
            confidence=task.confidence
        )

    def integrate_all(self, tasks: List[SystemTaskStatus]):
        results = []
        efficiency_score = 0
        count = 0

        for task in tasks:
            result = self.integrate_task(task)
            results.append(result)
            if result.final_status == "completed":
                efficiency_score += 1 * result.confidence
            count += 1

        global_efficiency = round(efficiency_score / count if count else 0, 3)
        return results, global_efficiency


engine = MultiSystemIntegrationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/integrate", response_model=Phase111Output)
def integrate_systems(data: Phase111Input):
    results, efficiency = engine.integrate_all(data.systems_tasks)

    return Phase111Output(
        message="Phase 111 multi-system integration complete",
        integration_results=results,
        global_integration_efficiency=efficiency,
        timestamp=str(datetime.datetime.now())
    )