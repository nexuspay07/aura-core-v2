import json
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path("memory/strategies.json")


class StrategyMemoryEngine:

    def __init__(self):
        self.memory = self.load_memory()

    def load_memory(self):
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memory, f, indent=4)

    def initialize_strategy(self, strategy_id, template="unknown"):
        if strategy_id not in self.memory:
            self.memory[strategy_id] = {
                "template": template,
                "wins": 0,
                "losses": 0,
                "usage_count": 0,
                "average_fitness": 0.0,
                "last_used": None
            }
            self.save_memory()

    def update_strategy(self, strategy_id, fitness, success):

        self.initialize_strategy(strategy_id)

        strategy = self.memory[strategy_id]

        strategy["usage_count"] += 1

        # update average fitness
        prev_avg = strategy["average_fitness"]
        count = strategy["usage_count"]

        strategy["average_fitness"] = ((prev_avg * (count - 1)) + fitness) / count

        if success:
            strategy["wins"] += 1
        else:
            strategy["losses"] += 1

        strategy["last_used"] = datetime.utcnow().isoformat()

        self.save_memory()

    def get_strategy_ranking(self):

        strategies = list(self.memory.items())

        ranked = sorted(
            strategies,
            key=lambda s: s[1]["average_fitness"],
            reverse=True
        )

        return ranked

    def get_best_strategy(self):

        ranked = self.get_strategy_ranking()

        if not ranked:
            return None

        return ranked[0][0]