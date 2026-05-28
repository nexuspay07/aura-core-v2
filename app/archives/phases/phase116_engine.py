from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime
import random

router = APIRouter(
    prefix="/phase116",
    tags=["Phase 116 — Autonomous Knowledge Expansion Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class SystemData(BaseModel):
    system_name: str
    new_data_points: int
    complexity_score: float  # how complex the new information is

class Phase116Input(BaseModel):
    global_mission: str
    systems_data: List[SystemData]


# ---------------------------
# Output Models
# ---------------------------

class KnowledgeUpdate(BaseModel):
    system_name: str
    insights_generated: int
    reasoning_improvement: float
    knowledge_growth_score: float

class Phase116Output(BaseModel):
    message: str
    knowledge_updates: List[KnowledgeUpdate]
    overall_knowledge_score: float
    timestamp: str


# ---------------------------
# Knowledge Expansion Engine
# ---------------------------

class KnowledgeExpansionEngine:

    def expand_knowledge(self, data: SystemData):
        # Simulate knowledge growth
        insights = data.new_data_points
        reasoning_gain = round(random.uniform(0.05, 0.2) * (1 - data.complexity_score), 3)
        knowledge_score = round(insights * reasoning_gain / 10, 3)

        return KnowledgeUpdate(
            system_name=data.system_name,
            insights_generated=insights,
            reasoning_improvement=reasoning_gain,
            knowledge_growth_score=knowledge_score
        )

    def expand_all(self, systems: List[SystemData]):
        updates = []
        total_score = 0
        for system in systems:
            update = self.expand_knowledge(system)
            updates.append(update)
            total_score += update.knowledge_growth_score
        overall_score = round(total_score / len(systems) if systems else 0, 3)
        return updates, overall_score


engine = KnowledgeExpansionEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/expand", response_model=Phase116Output)
def expand_knowledge(data: Phase116Input):
    updates, overall_score = engine.expand_all(data.systems_data)

    return Phase116Output(
        message="Phase 116 autonomous knowledge expansion complete",
        knowledge_updates=updates,
        overall_knowledge_score=overall_score,
        timestamp=str(datetime.datetime.now())
    )