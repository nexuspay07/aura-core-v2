from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(prefix="/phase85", tags=["Phase 85 — Autonomous Goal Generation"])


# INPUT
class SystemState(BaseModel):
    system_name: str
    efficiency_score: float  # 0–1
    risk_score: float        # 0–1
    growth_potential: float  # 0–1


class Phase85Input(BaseModel):
    systems: List[SystemState]


# OUTPUT
class GeneratedGoal(BaseModel):
    system_name: str
    generated_goal: str
    priority: str
    projected_impact: float


class Phase85Output(BaseModel):
    message: str
    generated_goals: List[GeneratedGoal]
    timestamp: str


class AutonomousGoalEngine:

    def generate_goals(self, systems):

        goals = []

        for system in systems:

            improvement_need = (
                (1 - system.efficiency_score) * 0.5 +
                system.risk_score * 0.3 +
                system.growth_potential * 0.2
            )

            improvement_need = round(improvement_need, 3)

            if improvement_need > 0.7:
                priority = "high"
            elif improvement_need > 0.4:
                priority = "medium"
            else:
                priority = "low"

            goal_text = f"Improve performance of {system.system_name}"

            goals.append(
                GeneratedGoal(
                    system_name=system.system_name,
                    generated_goal=goal_text,
                    priority=priority,
                    projected_impact=improvement_need
                )
            )

        goals.sort(key=lambda x: x.projected_impact, reverse=True)

        return goals


engine = AutonomousGoalEngine()


@router.post("/generate-goals", response_model=Phase85Output)
def generate_goals(data: Phase85Input):

    goals = engine.generate_goals(data.systems)

    return Phase85Output(
        message="Phase 85 autonomous goal generation complete",
        generated_goals=goals,
        timestamp=str(datetime.datetime.now())
    )