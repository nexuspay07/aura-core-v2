from fastapi import APIRouter
from app.core.cognitive_loop import cognitive_loop
from app.core.memory_engine import memory_engine

router = APIRouter(prefix="/cognitive", tags=["cognitive"])


@router.post("/start")
def start_cognitive_loop():
    cognitive_loop.start()
    return {"status": "Cognitive loop started"}


@router.post("/stop")
def stop_cognitive_loop():
    cognitive_loop.stop()
    return {"status": "Cognitive loop stopped"}


@router.get("/status")
def get_cognitive_status():
    return cognitive_loop.get_status()


@router.get("/memory/status")
def get_memory_status():
    return memory_engine.get_status()