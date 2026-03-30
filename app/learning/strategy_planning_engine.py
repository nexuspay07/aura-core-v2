class StrategyPlanningEngine:

    def __init__(self):

        print("[STRATEGY PLANNING ENGINE] Initialized")

    def generate_plan(self, strategy, knowledge_graph):

        plan = [strategy]

        current = strategy

        # Try building a 3-step plan
        for _ in range(2):

            children = knowledge_graph.get(current, [])

            if not children:
                break

            next_strategy = children[0]

            plan.append(next_strategy)

            current = next_strategy

        return plan


# Global instance
strategy_planning_engine = StrategyPlanningEngine()