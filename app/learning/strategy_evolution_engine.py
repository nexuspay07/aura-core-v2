# app/learning/strategy_evolution_engine.py
from app.learning.strategy_registry import strategy_registry
from app.learning.strategy_performance_tracker import strategy_performance_tracker

class StrategyEvolutionEngine:
    def evolve_strategies(self):
        strategies = strategy_registry.get_all_strategies()
        all_records = strategy_performance_tracker.get_recent_metrics()  # get all metrics

        for strategy in strategies:
            sid = getattr(strategy, "id", None) or getattr(strategy, "name", None) or str(strategy)

            # Filter all_records for this strategy
            records = [r for r in all_records if r.get("strategy_id") == sid]

            # Skip if no valid records
            if not records:
                continue

            # Ensure only valid dicts with 'score'
            valid_records = [r for r in records if isinstance(r, dict) and "score" in r]

            if not valid_records:
                continue

            avg_score = sum(r["score"] for r in valid_records) / len(valid_records)

            # Apply evolution logic
            if hasattr(strategy, "adapt"):
                strategy.adapt(avg_score)

            print(f"[STRATEGY EVOLUTION] Strategy {sid} evolved | Avg Score: {avg_score:.2f}")

# Singleton
strategy_evolution_engine = StrategyEvolutionEngine()