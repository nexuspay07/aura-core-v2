# app/learning/reinforcement_learning_engine.py

from app.learning.strategy_registry import strategy_registry
from app.learning.strategy_performance_tracker import strategy_performance_tracker

class ReinforcementLearningEngine:
    def __init__(self):
        # Initialize weights using strategy name or repr if no id exists
        self.strategy_weights = {}
        for s in strategy_registry.get_all_strategies():
            # Try to use .id, else .name, else str()
            sid = getattr(s, "id", None) or getattr(s, "name", None) or str(s)
            self.strategy_weights[sid] = 1.0

    def update_strategy_weights(self, n_recent=10, learning_rate=0.1):
        """
        Updates strategy weights based on recent performance.
        Uses the last n_recent records per strategy.
        """
        recent_records = strategy_performance_tracker.get_recent_metrics(n_recent)

        # Organize records by strategy
        records_by_strategy = {}
        for rec in recent_records:
            sid = rec["strategy_id"]
            if sid not in records_by_strategy:
                records_by_strategy[sid] = []
            records_by_strategy[sid].append(rec)

        # Update weights
        for sid, records in records_by_strategy.items():
            avg_score = sum(r["score"] for r in records) / len(records)
            old_weight = self.strategy_weights.get(sid, 1.0)
            new_weight = old_weight + learning_rate * (avg_score - old_weight)
            self.strategy_weights[sid] = max(0.01, new_weight)  # prevent zero/negative

    def get_strategy_weights(self):
        return self.strategy_weights


# Singleton
reinforcement_learning_engine = ReinforcementLearningEngine()