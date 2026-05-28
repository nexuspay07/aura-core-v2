from fastapi import APIRouter
from AURA.AURA_CORE_V2.app._archive.future_review.future_intelligence_expansion import intelligence_expansion_engine

router = APIRouter(prefix="/expansion", tags=["Intelligence Expansion"])


@router.post("/expand")
def expand_intelligence():

    result = intelligence_expansion_engine.expand()

    return {
        "status": "expanded",
        "details": result
    }


@router.get("/status")
def expansion_status():

    return intelligence_expansion_engine.get_status()