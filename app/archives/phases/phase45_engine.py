from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/phase45", tags=["Phase 45 — Intelligence Optimization"])


# INPUT MODEL (ONLY ONE FIELD)
class Phase45Input(BaseModel):
    previous_results: Dict[str, float]


# OUTPUT MODEL
class Phase45Output(BaseModel):
    message: str
    optimized_results: Dict[str, float]


# OPTIMIZER ENGINE
class IntelligenceOptimizer:

    def optimize(self, results: Dict[str, float]) -> Dict[str, float]:

        optimized = {}

        for key, value in results.items():

            base_score = float(value)

            improved = base_score * 1.1

            if improved > 1.0:
                improved = 1.0

            optimized[key] = improved

        return optimized


optimizer = IntelligenceOptimizer()


# ENDPOINT
@router.post("/optimize", response_model=Phase45Output)
def optimize_phase45(data: Phase45Input):

    optimized = optimizer.optimize(data.previous_results)

    return Phase45Output(
        message="Phase 45 optimization complete",
        optimized_results=optimized
    )