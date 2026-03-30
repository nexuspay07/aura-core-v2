import random


class StrategyFitnessEngine:

    def evaluate(self, strategy_data):

        score = 0

        efficiency = strategy_data.get("efficiency", 0)
        speed = strategy_data.get("speed", 0)
        cost = strategy_data.get("cost", 0)

        score += efficiency * 0.5
        score += speed * 0.3
        score += (100 - cost) * 0.2

        noise = random.uniform(-5, 5)

        return score + noise


strategy_fitness_engine = StrategyFitnessEngine()