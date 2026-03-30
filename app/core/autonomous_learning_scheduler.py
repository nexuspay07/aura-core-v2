# app/core/autonomous_learning_scheduler.py
from app.learning.strategy_performance_tracker import StrategyPerformanceTracker
from app.learning.reinforcement_learning_engine import ReinforcementLearningEngine

class AutonomousLearningScheduler:
    """Manages autonomous strategy learning."""

    def __init__(self):
        self.tracker = StrategyPerformanceTracker()
        self.rl_engine = ReinforcementLearningEngine(self.tracker)

    def record_strategy_performance(self, strategy_id: str, score: float, success: bool):
        """Add a new strategy record."""
        self.tracker.add_record(strategy_id, score, success)

    def run_learning_cycle(self):
        """Run a full RL update cycle."""
        print("[SCHEDULER] Running autonomous learning cycle...")
        self.rl_engine.update_strategy_weights()
        print("[SCHEDULER] Cycle complete.\n")