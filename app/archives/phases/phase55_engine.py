# app/engine/phase55_engine.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(prefix="/phase55", tags=["Phase 55 — Knowledge Synthesis"])

class Phase55Input(BaseModel):
    previous_knowledge: Dict[str, List[str]]  # goal -> list of insights

class Phase55Output(BaseModel):
    message: str
    synthesized_knowledge: Dict[str, str]  # goal -> summary

class KnowledgeSynthesizer:
    """Phase 55: Combine all knowledge into structured insights."""
    def synthesize(self, knowledge: Dict[str, List[str]]) -> Dict[str, str]:
        synthesized = {}
        for goal, insights in knowledge.items():
            # Simple synthesis: combine insights into a single coherent summary
            summary = " ".join(sorted(insights, key=lambda x: len(x)))  # order by length for variety
            synthesized[goal] = summary
        return synthesized

synthesizer = KnowledgeSynthesizer()

@router.post("/synthesize", response_model=Phase55Output)
async def synthesize_phase55(data: Phase55Input):
    result = synthesizer.synthesize(data.previous_knowledge)
    return Phase55Output(
        message="Phase 55 knowledge synthesis complete",
        synthesized_knowledge=result
    )