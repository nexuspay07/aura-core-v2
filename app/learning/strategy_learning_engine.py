from app.learning.strategy_darwin_engine import StrategyDarwinEngine
from app.learning.strategy_memory_engine import StrategyMemoryEngine


class StrategyLearningEngine:
    """
    Strategy Learning Engine

    Responsible for:
    - Executing strategies
    - Evaluating strategy fitness
    - Updating strategy memory
    """

    def __init__(self):
        self.memory_engine = StrategyMemoryEngine()
        self.darwin_engine = StrategyDarwinEngine()

    def evaluate_strategy(self, strategy_id, fitness_score):
        """
        Evaluate strategy performance and store learning data.
        """

        success = fitness_score > 0.6

        self.memory_engine.update_strategy(
            strategy_id=strategy_id,
            fitness=fitness_score,
            success=success
        )

        return {
            "strategy_id": strategy_id,
            "fitness": fitness_score,
            "success": success
        }

    def select_strategy(self):
        """
        Select the best strategy using Darwin selection.
        """

        strategy_id = self.darwin_engine.select_best_strategy()

        return strategy_id

    def run_learning_cycle(self, strategy_id, fitness_score):
        """
        Complete learning cycle.
        """

        result = self.evaluate_strategy(strategy_id, fitness_score)

        return {
            "learning_update": result
        }