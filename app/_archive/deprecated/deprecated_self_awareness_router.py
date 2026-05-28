from fastapi import APIRouter

from app.core.self_awareness import self_awareness

router = APIRouter(prefix="/self", tags=["Self Awareness"])


@router.get("/status")
def get_self_status():

    return self_awareness.evaluate_self()