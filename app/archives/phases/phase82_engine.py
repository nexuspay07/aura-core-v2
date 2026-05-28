from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(prefix="/phase82", tags=["Phase 82 — Ethical & Safety Governance"])


# INPUT
class StrategyEvaluation(BaseModel):
    action: str
    risk_level: float  # 0 = no risk, 1 = extreme risk
    compliance_score: float  # 0 = non-compliant, 1 = fully compliant


class Phase82Input(BaseModel):
    strategies: List[StrategyEvaluation]


# OUTPUT
class GovernanceResult(BaseModel):
    action: str
    approved: bool
    governance_score: float
    reason: str


class Phase82Output(BaseModel):
    message: str
    governance_results: List[GovernanceResult]
    approved_actions: List[str]
    timestamp: str


class EthicalGovernanceEngine:

    def evaluate(self, strategies):

        results = []
        approved_actions = []

        for strategy in strategies:

            governance_score = round(
                (strategy.compliance_score * 0.7) +
                ((1 - strategy.risk_level) * 0.3),
                3
            )

            approved = governance_score >= 0.6

            if approved:
                reason = "Approved — meets ethical and safety standards"
                approved_actions.append(strategy.action)
            else:
                reason = "Blocked — insufficient safety or compliance score"

            results.append(
                GovernanceResult(
                    action=strategy.action,
                    approved=approved,
                    governance_score=governance_score,
                    reason=reason
                )
            )

        return results, approved_actions


engine = EthicalGovernanceEngine()


@router.post("/govern", response_model=Phase82Output)
def govern(data: Phase82Input):

    results, approved = engine.evaluate(data.strategies)

    return Phase82Output(
        message="Phase 82 ethical governance complete",
        governance_results=results,
        approved_actions=approved,
        timestamp=str(datetime.datetime.now())
    )