import random


class MultiPlanExplorationEngine:

    def __init__(self):

        print("[MULTI PLAN EXPLORATION ENGINE] Initialized")

    def generate_plan_variations(self, base_plan):

        plans = []

        # Always include original plan
        plans.append(base_plan)

        # Create variations
        for _ in range(2):

            variation = base_plan.copy()

            if random.random() < 0.5:
                variation = list(reversed(base_plan))

            plans.append(variation)

        return plans

    def choose_best_plan(self, simulations):

        best = None
        best_score = -1

        for sim in simulations:

            score = sim["simulated_score"]

            if score > best_score:
                best_score = score
                best = sim

        return best


# Global instance
multi_plan_exploration_engine = MultiPlanExplorationEngine()