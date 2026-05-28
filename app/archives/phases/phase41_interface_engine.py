from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class AuraInput(BaseModel):
    source: str
    message: str


class AuraResponse(BaseModel):
    aura_response: str
    timestamp: str
    phase: int


@router.post("/aura/interface", response_model=AuraResponse)
def aura_interface(input_data: AuraInput):

    # Basic reasoning simulation
    processed = f"Aura received from {input_data.source}: {input_data.message}"

    return AuraResponse(
        aura_response=processed,
        timestamp=datetime.utcnow().isoformat(),
        phase=41
    )