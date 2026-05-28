from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.database import get_db
from app.memory.memory_models import AuraMemory
from app.memory.memory_schema import MemoryCreate, MemoryResponse


router = APIRouter(
    prefix="/memory",
    tags=["Memory"]
)


# Store memory
@router.post("/store", response_model=MemoryResponse)
def store_memory(memory: MemoryCreate, db: Session = Depends(get_db)):

    new_memory = AuraMemory(
        id=str(uuid.uuid4()),
        organization_id=memory.organization_id,
        content=memory.content,
        memory_type=memory.memory_type,
        created_at=datetime.utcnow()
    )

    db.add(new_memory)
    db.commit()
    db.refresh(new_memory)

    return new_memory


# Retrieve organization memory
@router.get("/{organization_id}")
def get_memory(organization_id: str, db: Session = Depends(get_db)):

    memories = db.query(AuraMemory).filter(
        AuraMemory.organization_id == organization_id
    ).all()

    return memories


# Memory system status
@router.get("/status")
def memory_status():
    return {
        "memory_system": "ACTIVE",
        "status": "operational"
    }