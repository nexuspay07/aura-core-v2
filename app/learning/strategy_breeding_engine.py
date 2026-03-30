import random
from app.learning.strategy_genome_engine import strategy_genome_engine


class StrategyBreedingEngine:

    def __init__(self):

        self.hybrids = {}

        print("[STRATEGY BREEDING ENGINE] Initialized")

    def breed(self, strategy_a, strategy_b):

        genome_a = strategy_genome_engine.create_genome(strategy_a)
        genome_b = strategy_genome_engine.create_genome(strategy_b)

        hybrid_name = f"{strategy_a}_{strategy_b}_hybrid"

        hybrid_genome = {
            "strategy": hybrid_name,
            "speed": (genome_a["speed"] + genome_b["speed"]) / 2,
            "efficiency": (genome_a["efficiency"] + genome_b["efficiency"]) / 2,
            "resource_usage": (genome_a["resource_usage"] + genome_b["resource_usage"]) / 2,
            "risk": (genome_a["risk"] + genome_b["risk"]) / 2
        }

        self.hybrids[hybrid_name] = hybrid_genome

        print("[STRATEGY HYBRID CREATED]", hybrid_genome)

        return hybrid_genome


# Global instance
strategy_breeding_engine = StrategyBreedingEngine()