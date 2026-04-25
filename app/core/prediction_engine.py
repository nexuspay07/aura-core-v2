from copy import deepcopy


class PredictionEngine:
    def __init__(self):
        self.last_predictions = []
        print("[PREDICTION ENGINE] Initialized")

    def simulate_strategy(self, strategy: dict, world_state: dict):
        """
        Predict likely outcome of a strategy using current world state.
        Works with Aura's current dict-based strategy format.
        """
        predicted_state = deepcopy(world_state)

        strategy_name = strategy.get("name", "Unknown")
        base_score = strategy.get("final_score", strategy.get("score", 0))
        risk = strategy.get("risk", "medium")
        confidence = strategy.get("confidence", 0.7)

        market_growth = predicted_state.get("market_growth", 0.5)
        competition = predicted_state.get("competition", 0.5)
        risk_level = predicted_state.get("risk_level", 0.5)
        budget = predicted_state.get("budget", 10000)

        outcome_bonus = 0

        # Strategy-specific future behavior
        if strategy_name == "Aggressive":
            outcome_bonus += market_growth * 1.2
            outcome_bonus -= competition * 0.7
            outcome_bonus -= risk_level * 0.8
            if budget > 8000:
                outcome_bonus += 0.4

        elif strategy_name == "Balanced":
            outcome_bonus += market_growth * 0.8
            outcome_bonus -= competition * 0.4
            outcome_bonus -= risk_level * 0.3
            outcome_bonus += 0.2

        elif strategy_name == "Conservative":
            outcome_bonus += market_growth * 0.4
            outcome_bonus -= competition * 0.2
            outcome_bonus -= risk_level * 0.1
            if risk_level < 0.4:
                outcome_bonus += 0.3

        # Risk adjustment
        if risk == "high":
            risk_penalty = 0.6
        elif risk == "medium":
            risk_penalty = 0.3
        else:
            risk_penalty = 0.1

        predicted_score = base_score + outcome_bonus - risk_penalty
        predicted_score *= confidence

        prediction = {
            "strategy": strategy_name,
            "base_score": round(base_score, 2),
            "predicted_score": round(predicted_score, 2),
            "predicted_growth": round(outcome_bonus, 2),
            "risk_penalty": round(risk_penalty, 2),
            "confidence_used": round(confidence, 2),
            "world_factors": {
                "market_growth": round(market_growth, 2),
                "competition": round(competition, 2),
                "risk_level": round(risk_level, 2),
                "budget": budget
            }
        }

        return prediction

    def simulate_multiple(self, strategies: list, world_state: dict):
        predictions = [
            self.simulate_strategy(strategy, world_state)
            for strategy in strategies
        ]
        self.last_predictions = predictions
        return predictions

    def rank_strategies(self, predictions: list):
        return sorted(
            predictions,
            key=lambda x: x["predicted_score"],
            reverse=True
        )

    def enrich_strategies_with_predictions(self, strategies: list, world_state: dict):
        """
        Add prediction output back into strategy dicts.
        """
        predictions = self.simulate_multiple(strategies, world_state)
        prediction_map = {
            p["strategy"]: p for p in predictions
        }

        for strategy in strategies:
            name = strategy.get("name")
            if name in prediction_map:
                strategy["prediction"] = prediction_map[name]
                strategy["predicted_score"] = prediction_map[name]["predicted_score"]

        return strategies

    def get_last_predictions(self):
        return self.last_predictions


prediction_engine = PredictionEngine()