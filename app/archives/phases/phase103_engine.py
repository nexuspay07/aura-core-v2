from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(
    prefix="/phase103",
    tags=["Phase 103 — Strategic Self-Architecting Simulation Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemStrategicState(BaseModel):
    enterprise_id: str
    system_name: str
    current_performance: float
    resource_usage: float
    growth_trend: float
    risk_level: float


class Phase103Input(BaseModel):
    global_mission: str
    planning_horizon_years: int
    systems: List[SystemStrategicState]


# ---------------------------
# Output Models
# ---------------------------

class StrategicRecommendation(BaseModel):
    enterprise_id: str
    system_name: str
    predicted_future_performance: float
    recommended_priority: str
    recommended_action: str
    risk_projection: float


class Phase103Output(BaseModel):
    message: str
    global_mission: str
    planning_horizon_years: int
    strategic_recommendations: List[StrategicRecommendation]
    overall_future_readiness_score: float
    timestamp: str


# ---------------------------
# Strategic Simulation Engine
# ---------------------------

class StrategicSelfArchitectingEngine:

    def simulate_future(self, system: SystemStrategicState, horizon: int):

        growth_factor = system.growth_trend * horizon
        performance_projection = system.current_performance + growth_factor

        performance_projection = max(0, min(1, performance_projection))

        risk_projection = system.risk_level + random.uniform(-0.05, 0.05)
        risk_projection = max(0, min(1, risk_projection))

        return performance_projection, risk_projection


    def determine_priority(self, performance, risk):

        if risk > 0.7:
            return "CRITICAL"

        elif performance < 0.6:
            return "HIGH"

        elif performance < 0.8:
            return "MEDIUM"

        else:
            return "LOW"


    def determine_action(self, priority):

        if priority == "CRITICAL":
            return "Immediate architectural reinforcement and resource reallocation"

        elif priority == "HIGH":
            return "Deploy optimization modules and increase learning allocation"

        elif priority == "MEDIUM":
            return "Monitor and incrementally optimize"

        else:
            return "Maintain current configuration"


    def run_simulation(self, systems: List[SystemStrategicState], horizon: int):

        recommendations = []
        total_score = 0

        for system in systems:

            future_performance, risk_projection = self.simulate_future(system, horizon)

            priority = self.determine_priority(future_performance, risk_projection)

            action = self.determine_action(priority)

            recommendations.append(
                StrategicRecommendation(
                    enterprise_id=system.enterprise_id,
                    system_name=system.system_name,
                    predicted_future_performance=round(future_performance, 3),
                    recommended_priority=priority,
                    recommended_action=action,
                    risk_projection=round(risk_projection, 3)
                )
            )

            readiness_score = future_performance * (1 - risk_projection)
            total_score += readiness_score

        overall_readiness = total_score / len(systems) if systems else 0

        return recommendations, round(overall_readiness, 3)


engine = StrategicSelfArchitectingEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/strategic-simulate", response_model=Phase103Output)
def strategic_self_architect(data: Phase103Input):

    recommendations, readiness_score = engine.run_simulation(
        data.systems,
        data.planning_horizon_years
    )

    return Phase103Output(
        message="Phase 103 strategic self-architecting simulation complete",
        global_mission=data.global_mission,
        planning_horizon_years=data.planning_horizon_years,
        strategic_recommendations=recommendations,
        overall_future_readiness_score=readiness_score,
        timestamp=str(datetime.datetime.now())
    )