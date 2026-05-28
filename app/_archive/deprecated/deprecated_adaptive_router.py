from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.memory.memory_models import AuraMemory
from app.core.adaptive_core import AdaptiveCore


# Create router object ← THIS IS WHAT main.py NEEDS
router = APIRouter(
    prefix="/adaptive",
    tags=["Adaptive Intelligence"]
)


adaptive_core = AdaptiveCore()


# Adaptive learning endpoint
@router.post("/learn")
def adaptive_learn(organization_id: str, db: Session = Depends(get_db)):

    memories = db.query(AuraMemory).filter(
        AuraMemory.organization_id == organization_id
    ).all()

    result = adaptive_core.learn(memories)

    return {
        "status": "learning_complete",
        "organization_id": organization_id,
        "patterns_learned": result,
        "timestamp": datetime.utcnow()
    }


# Adaptive intelligence status
@router.get("/status")
def adaptive_status():

    return {
        "adaptive_core": "ACTIVE",
        "learning": True,
        "version": "Phase 125"
    }