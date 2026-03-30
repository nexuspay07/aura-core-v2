from fastapi import APIRouter
from app.core.self_improvement_engine import self_improvement_engine

router = APIRouter(prefix="/improvement", tags=["Self Improvement"])


@router.get("/status")
def improvement_status():

    return self_improvement_engine.get_status()