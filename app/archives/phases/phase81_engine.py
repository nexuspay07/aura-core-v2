from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import datetime

router = APIRouter(prefix="/phase81", tags=["Phase 81 — Adaptive Strategy Evolution"])

# INPUT
class StrategyOutcome(BaseModel):
    action: str
    outcome_score: float  # Real-world performance (0-1)


class Phase81Input(BaseModel):
    historical_outcomes: List[StrategyOutcome]


# OUTPUT
class StrategyRanking(BaseModel):
    action: str
    average_score: float
    preference_weight: float


class Phase81Output(BaseModel):
    message: str
    ranked_strategies: List[StrategyRanking]
    recommended_primary_strategy: str
    timestamp: str


class AdaptiveStrategyEngine:

    def evolve_strategies(self, historical_outcomes):

        strategy_scores = {}

        # Aggregate scores
        for outcome in historical_outcomes:
            if outcome.action not in strategy_scores:
                strategy_scores[outcome.action] = []

            strategy_scores[outcome.action].append(outcome.outcome_score)

        ranked = []

        for action, scores in strategy_scores.items():
            avg_score = sum(scores) / len(scores)
            preference_weight = round(avg_score * 1.2, 3)  # Slight reinforcement boost

            ranked.append(
                StrategyRanking(
                    action=action,
                    average_score=round(avg_score, 3),
                    preference_weight=preference_weight
                )
            )

        ranked.sort(key=lambda x: x.preference_weight, reverse=True)

        primary_strategy = ranked[0].action if ranked else "No strategy available"

        return ranked, primary_strategy


engine = AdaptiveStrategyEngine()


@router.post("/evolve-strategies", response_model=Phase81Output)
def evolve_strategies(data: Phase81Input):

    ranked, primary = engine.evolve_strategies(data.historical_outcomes)

    return Phase81Output(
        message="Phase 81 adaptive strategy evolution complete",
        ranked_strategies=ranked,
        recommended_primary_strategy=primary,
        timestamp=str(datetime.datetime.now())
    )