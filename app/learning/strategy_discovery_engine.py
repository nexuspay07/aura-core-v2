# app/learning/strategy_discovery_engine.py

import random
import uuid

from app.learning.strategy_registry import strategy_registry, Strategy


class StrategyDiscoveryEngine:

    def __init__(self):

        self.discovery_rate = 0.3  # probability of discovering a strategy

        print("[STRATEGY DISCOVERY] Engine Initialized")

    # -----------------------------------------------------

    def discover_strategy(self, goal, plan, score):

        """
        Analyze a successful plan and possibly create a new strategy
        """

        if score < 0.7:
            return None

        if random.random() > self.discovery_rate:
            return None

        strategy_id = str(uuid.uuid4())[:8]

        strategy_name = f"Discovered Strategy {strategy_id}"

        parameters = self.extract_parameters_from_plan(plan)

        new_strategy = Strategy(
            strategy_id=strategy_id,
            name=strategy_name,
            parameters=parameters
        )

        strategy_registry.register_strategy(new_strategy)

        print(
            f"[STRATEGY DISCOVERY] New strategy discovered: {strategy_name}"
        )

        return new_strategy

    # -----------------------------------------------------

    def extract_parameters_from_plan(self, plan):

        """
        Extract simple behavioral parameters from the plan
        """

        step_count = len(plan)

        parameters = {
            "complexity": step_count,
            "planning_depth": min(step_count, 10),
            "risk": round(random.uniform(0.2, 0.8), 2)
        }

        return parameters


# Singleton
strategy_discovery_engine = StrategyDiscoveryEngine()