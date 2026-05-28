# phase53_engine.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(prefix="/phase53", tags=["Phase 53 — Multi-Domain Intelligence"])

class Phase53Input(BaseModel):
    goal: str
    domain_results: Dict[str, Dict[str, Any]]  # Results from multiple domains

class Phase53Output(BaseModel):
    message: str
    combined_insights: List[str]

class MultiDomainEngine:
    """Phase 53: Integrate insights from multiple domains for unified intelligence."""
    def integrate(self, goal: str, domain_results: Dict[str, Dict[str, Any]]) -> List[str]:
        insights = []
        for domain, results in domain_results.items():
            for key, value in results.items():
                score = float(value) if isinstance(value, (int, float)) else 0.5
                if score > 0.7:
                    insights.append(f"[{domain}] Strong factor for {goal}: {key}")
                else:
                    insights.append(f"[{domain}] Moderate factor for {goal}: {key}")
        return insights

engine = MultiDomainEngine()

@router.post("/integrate", response_model=Phase53Output)
async def integrate_phase53(data: Phase53Input):
    combined_insights = engine.integrate(data.goal, data.domain_results)
    return Phase53Output(
        message=f"Phase 53 multi-domain intelligence complete for goal '{data.goal}'",
        combined_insights=combined_insights
    )