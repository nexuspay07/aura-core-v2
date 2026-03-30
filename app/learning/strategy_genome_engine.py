import random


class StrategyGenomeEngine:

    def __init__(self):

        self.genomes = {}

        print("[STRATEGY GENOME ENGINE] Initialized")

    def create_genome(self, strategy):

        if strategy in self.genomes:
            return self.genomes[strategy]

        genome = {
            "strategy": strategy,
            "speed": random.uniform(0.3, 1.0),
            "efficiency": random.uniform(0.3, 1.0),
            "resource_usage": random.uniform(0.3, 1.0),
            "risk": random.uniform(0.1, 0.9)
        }

        self.genomes[strategy] = genome

        print("[GENOME CREATED]", genome)

        return genome

    def evolve_genome(self, strategy):

        genome = self.create_genome(strategy)

        mutation_factor = random.uniform(-0.05, 0.05)

        genome["speed"] += mutation_factor
        genome["efficiency"] += mutation_factor
        genome["resource_usage"] += mutation_factor

        print("[GENOME EVOLVED]", genome)

        return genome


# Global instance
strategy_genome_engine = StrategyGenomeEngine()