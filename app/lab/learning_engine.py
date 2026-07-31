from typing import Dict, List

from sqlalchemy.orm import Session

from app.lab.history_engine import history_engine


class LearningEngine:
    """
    Learns from previous simulation history and applies
    context-aware learning bonuses to future strategies.
    """

    def __init__(self):
        self.learning_rate = 0.2

    # ==========================================================
    # BUILD CONTEXT KEY
    # ==========================================================

    def build_context_key(
        self,
        strategy_name: str,
        scenario: Dict,
    ) -> str:

        risk = scenario.get("risk_tolerance", 0.5)
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")

        risk_level = (
            "high_risk"
            if risk > 0.6
            else "low_risk"
        )

        budget_level = (
            "high_budget"
            if budget > 8000
            else "low_budget"
        )

        return (
            f"{strategy_name}|"
            f"{risk_level}|"
            f"{budget_level}|"
            f"{market}"
        )

    # ==========================================================
    # LEARN FROM HISTORY
    # ==========================================================

    async def learn(
        self,
        db: Session,
        organization_id: int,
    ) -> Dict[str, float]:

        history = history_engine.get(
            db=db,
            organization_id=organization_id,
        )

        if not history:
            return {}

        context_scores = {}
        context_counts = {}

        for record in history:

            scenario = record.get("scenario", {})
            result = record.get("result", {})

            strategies = result.get(
                "results",
                [],
            )

            for strategy in strategies:

                name = strategy.get("name")

                score = strategy.get(
                    "final_score",
                    strategy.get("score", 0),
                )

                key = self.build_context_key(
                    name,
                    scenario,
                )

                context_scores[key] = (
                    context_scores.get(key, 0)
                    + score
                )

                context_counts[key] = (
                    context_counts.get(key, 0)
                    + 1
                )

        learned_patterns = {}

        for key in context_scores:

            average = (
                context_scores[key]
                / context_counts[key]
            )

            learned_patterns[key] = round(
                average * self.learning_rate,
                4,
            )

        return learned_patterns

    # ==========================================================
    # APPLY LEARNING
    # ==========================================================

    def apply_learning(
        self,
        strategies: List[Dict],
        scenario: Dict,
        patterns: Dict[str, float],
    ) -> List[Dict]:

        for strategy in strategies:

            key = self.build_context_key(
                strategy["name"],
                scenario,
            )

            bonus = patterns.get(
                key,
                0.0,
            )

            strategy["learning_bonus"] = round(
                bonus,
                4,
            )

            strategy["learning_context_key"] = key

            if bonus:

                strategy["score"] = (
                    strategy.get("score", 0)
                    + bonus
                )

        return strategies


learning_engine = LearningEngine()