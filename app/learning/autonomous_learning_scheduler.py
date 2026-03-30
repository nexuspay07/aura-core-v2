# app/learning/autonomous_learning_scheduler.py

import time
from app.learning.strategy_registry import strategy_registry
from app.learning.strategy_performance_tracker import strategy_performance_tracker
from app.learning.strategy_simulation_engine import StrategySimulationEngine
from app.learning.reinforcement_learning_engine import reinforcement_learning_engine

class AutonomousLearningScheduler:

    def __init__(self):
        self.simulation_engine = StrategySimulationEngine(
            strategy_registry,
            strategy_performance_tracker
        )
        self.last_run = None  # timestamp of last learning cycle

    def schedule_learning(self, strategies=None, resource_state=None, past_performance=None):
        """
        Automatically decide which strategies to retrain and when
        """
        # Use all strategies if not provided
        strategies = strategies or strategy_registry.get_all_strategies()

        # Basic scheduling logic: only run if resources are sufficient
        if resource_state:
            if resource_state.get("cpu", 0) > 80 or resource_state.get("memory", 0) > 90:
                print("[LEARNING SCHEDULER] Resources too high, deferring learning cycle")
                return

        # Check for underperforming strategies
        low_perf_strategies = []
        if past_performance:
            for s_id, metrics in past_performance.items():
                if metrics.get("success_rate", 1.0) < 0.8:
                    low_perf_strategies.append(s_id)
        else:
            # If no metrics, schedule all strategies
            low_perf_strategies = [str(s.id) for s in strategies]

        # Run simulation for selected strategies
        for s_id in low_perf_strategies:
            strategy = next((s for s in strategies if str(getattr(s, "id", s)) == str(s_id)), None)
            if strategy:
                print(f"[LEARNING SCHEDULER] Retraining strategy: {s_id}")
                self.simulation_engine.simulate_strategy(strategy)

        # Update reinforcement learning weights after training
        reinforcement_learning_engine.update_strategy_weights()
        print("[LEARNING SCHEDULER] Learning cycle complete")

        self.last_run = time.time()


# Singleton instance
learning_scheduler_engine = AutonomousLearningScheduler()