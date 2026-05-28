from fastapi import APIRouter
from app.core.decision_engine import decision_engine

router = APIRouter(prefix="/decision", tags=["Decision Engine"])


@router.post("/make")
def make_decision(input_data: dict):
    result = decision_engine.make_decision(input_data)
    return result


@router.get("/status")
def decision_status():
    return decision_engine.get_status()