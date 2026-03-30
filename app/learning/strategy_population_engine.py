import random


class StrategyPopulationEngine:

    def __init__(self):

        self.population = {}

        print("[STRATEGY POPULATION ENGINE] Initialized")

    def update_population(self, strategy, reward):

        if strategy not in self.population:

            self.population[strategy] = {
                "fitness": 0,
                "age": 0
            }

        # Update fitness
        self.population[strategy]["fitness"] += reward

        # Increase age
        self.population[strategy]["age"] += 1

        return self.population[strategy]

    def natural_selection(self):

        if len(self.population) < 3:
            return None

        weakest = min(
            self.population,
            key=lambda s: self.population[s]["fitness"]
        )

        removed = self.population.pop(weakest)

        print("[NATURAL SELECTION] Removed strategy:", weakest)

        return {
            "removed_strategy": weakest,
            "data": removed
        }


# Global instance
strategy_population_engine = StrategyPopulationEngine()