from fastapi import APIRouter
from app.core.intelligence_orchestrator import intelligence_orchestrator

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.post("/process")
def process_intelligence(input_data: dict):

    result = intelligence_orchestrator.process(input_data)

    return result


@router.get("/status")
def intelligence_status():

    return intelligence_orchestrator.get_status()


@router.get("/execution/status")
async def execution_status():

    return cognitive_loop.execution_engine.get_status()