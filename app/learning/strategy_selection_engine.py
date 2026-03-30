from app.learning.reinforcement_learning_engine import reinforcement_learning_engine

import json
import os
import random


class StrategySelectionEngine:

    def __init__(self):

        self.strategies = [
            {"id": 1, "name": "Exploration Strategy"},
            {"id": 2, "name": "Efficiency Strategy"},
            {"id": 3, "name": "Balanced Strategy"}
        ]

        self.weights_file = "data/strategy_weights.json"

    def select_strategy(self, goal):

        weights = {}

        if os.path.exists(self.weights_file):

            with open(self.weights_file, "r") as f:
                weights = json.load(f)

        scored_strategies = []

        for strategy in self.strategies:

            strategy_id = strategy["id"]

            weight = weights.get(str(strategy_id), 0.5)

            scored_strategies.append((strategy, weight))

        scored_strategies.sort(key=lambda x: x[1], reverse=True)

        selected_strategy = scored_strategies[0][0]

        print(
            f"[STRATEGY SELECTION] Selected Strategy {selected_strategy['id']} "
            f"for Goal '{goal['name']}'"
        )

        return selected_strategy


strategy_selection_engine = StrategySelectionEngine()