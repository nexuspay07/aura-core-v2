# app/core/prediction_engine.py

from app.core.world_modeling_engine import world_modeling_engine

class PredictionEngine:
    def __init__(self):
        self.last_predictions = {}
        print("[PREDICTION ENGINE] Initialized")

    def simulate_strategy(self, strategy, world_state):
        """
        Simulate a strategy based on current world state.
        Returns predicted world state and score.
        """
        # Clone the world state to avoid mutating actual model
        predicted_state = world_state.copy()

        # Example: simple prediction logic
        # Here, we simulate effects based on strategy attributes
        if hasattr(strategy, "effects"):
            for var, change in strategy.effects.items():
                if var in predicted_state:
                    predicted_state[var] += change

        # Compute a simple score (can be more complex)
        score = predicted_state.get("profit", 0) / (predicted_state.get("cost", 1))
        
        return {"strategy_id": getattr(strategy, "id", str(strategy)),
                "predicted_state": predicted_state,
                "score": score}

    def simulate_multiple(self, strategies, world_state):
        """
        Simulate multiple strategies and return predictions.
        """
        predictions = []
        for strategy in strategies:
            pred = self.simulate_strategy(strategy, world_state)
            predictions.append(pred)
        self.last_predictions = predictions
        return predictions

    def rank_strategies(self, predictions):
        """
        Rank strategies based on predicted score (higher = better)
        """
        return sorted(predictions, key=lambda x: x["score"], reverse=True)

    def get_last_predictions(self):
        return self.last_predictions

# Singleton instance
prediction_engine = PredictionEngine()