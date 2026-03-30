from fastapi import APIRouter
from app.core.evolution_engine import EvolutionEngine
from app.core.decision_engine import decision_engine
from app.memory.memory_manager import memory_manager


router = APIRouter(
    prefix="/evolution",
    tags=["Evolution Engine"]
)

evolution_engine = EvolutionEngine(memory_manager, decision_engine)


@router.post("/analyze/{organization_id}")
def analyze(organization_id: str):
    return evolution_engine.analyze_self(organization_id)


@router.post("/evolve/{organization_id}")
def evolve(organization_id: str):
    return evolution_engine.evolve(organization_id)


@router.get("/status")
def status():
    return evolution_engine.get_status()


@router.get("/history")
def history():
    return evolution_engine.get_history()