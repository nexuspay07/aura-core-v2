# app/learning/strategy_darwin_engine.py

import random
from app.learning.strategy_registry import strategy_registry

class StrategyDarwinEngine:

    def __init__(self, epsilon=0.2):
        """
        epsilon: probability to explore a random strategy
        """
        self.strategy_scores = {}  # strategy_id -> fitness
        self.epsilon = epsilon

    def select_best_strategy(self):
        """
        Returns strategy_id
        """
        strategies = strategy_registry.get_all_strategies()

        if not strategies:
            return None

        # Exploration
        if random.random() < self.epsilon:
            return random.choice(strategies).strategy_id

        # Exploitation
        if not self.strategy_scores:
            # No scores yet, pick first
            return strategies[0].strategy_id

        # Pick highest fitness
        sorted_strategies = sorted(
            self.strategy_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )
        return sorted_strategies[0][0]

    def record_strategy_result(self, strategy_id, fitness_score):
        self.strategy_scores[strategy_id] = fitness_score


strategy_darwin_engine = StrategyDarwinEngine(epsilon=0.3)  # 30% exploration