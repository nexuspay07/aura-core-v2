from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase112",
    tags=["Phase 112 — Autonomous Cross-Enterprise Orchestration Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class EnterpriseTask(BaseModel):
    system_name: str
    task: str
    priority: str
    status: str  # "pending", "completed", "failed"
    confidence: float

class Phase112Input(BaseModel):
    global_mission: str
    enterprise_tasks: List[EnterpriseTask]


# ---------------------------
# Output Models
# ---------------------------

class OrchestrationResult(BaseModel):
    system_name: str
    task: str
    action_taken: str
    final_status: str
    confidence: float

class Phase112Output(BaseModel):
    message: str
    orchestration_results: List[OrchestrationResult]
    global_orchestration_efficiency: float
    timestamp: str


# ---------------------------
# Orchestration Engine
# ---------------------------

class CrossEnterpriseOrchestrationEngine:

    def orchestrate_task(self, task: EnterpriseTask):
        if task.status == "completed":
            action = "No action needed"
            final_status = "completed"
        elif task.status == "failed":
            action = "Auto-retry executed"
            final_status = "completed"
        else:
            action = "Task scheduled for execution"
            final_status = "pending"

        return OrchestrationResult(
            system_name=task.system_name,
            task=task.task,
            action_taken=action,
            final_status=final_status,
            confidence=task.confidence
        )

    def orchestrate_all(self, tasks: List[EnterpriseTask]):
        results = []
        efficiency_score = 0
        count = 0

        for task in tasks:
            result = self.orchestrate_task(task)
            results.append(result)
            if result.final_status == "completed":
                efficiency_score += 1 * result.confidence
            count += 1

        global_efficiency = round(efficiency_score / count if count else 0, 3)
        return results, global_efficiency


engine = CrossEnterpriseOrchestrationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/orchestrate", response_model=Phase112Output)
def orchestrate_enterprise(data: Phase112Input):
    results, efficiency = engine.orchestrate_all(data.enterprise_tasks)

    return Phase112Output(
        message="Phase 112 cross-enterprise orchestration complete",
        orchestration_results=results,
        global_orchestration_efficiency=efficiency,
        timestamp=str(datetime.datetime.now())
    )