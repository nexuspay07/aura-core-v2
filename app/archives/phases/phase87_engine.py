from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase87", tags=["Phase 87 — Autonomous System Control"])


# INPUT
class ExecutableAction(BaseModel):
    system_name: str
    action: str
    governance_approved: bool


class Phase87Input(BaseModel):
    actions: List[ExecutableAction]


# OUTPUT
class ExecutionResult(BaseModel):
    system_name: str
    action: str
    executed: bool
    success_rate: float
    anomaly_detected: bool


class Phase87Output(BaseModel):
    message: str
    execution_results: List[ExecutionResult]
    overall_success_score: float
    timestamp: str


class AutonomousControlEngine:

    def execute(self, actions):

        results = []
        total_success = 0
        count = 0

        for item in actions:

            if not item.governance_approved:
                results.append(
                    ExecutionResult(
                        system_name=item.system_name,
                        action=item.action,
                        executed=False,
                        success_rate=0.0,
                        anomaly_detected=False
                    )
                )
                continue

            success_rate = round(random.uniform(0.7, 1.0), 3)
            anomaly = success_rate < 0.75

            total_success += success_rate
            count += 1

            results.append(
                ExecutionResult(
                    system_name=item.system_name,
                    action=item.action,
                    executed=True,
                    success_rate=success_rate,
                    anomaly_detected=anomaly
                )
            )

        overall = round(total_success / count, 3) if count > 0 else 0.0

        return results, overall


engine = AutonomousControlEngine()


@router.post("/execute-actions", response_model=Phase87Output)
def execute_actions(data: Phase87Input):

    results, overall = engine.execute(data.actions)

    return Phase87Output(
        message="Phase 87 autonomous system control execution complete",
        execution_results=results,
        overall_success_score=overall,
        timestamp=str(datetime.datetime.now())
    )