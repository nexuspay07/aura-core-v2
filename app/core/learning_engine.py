# app/core/learning_engine.py

import time

class LearningEngine:
    def __init__(self):
        self.strategies = [
            {"id": 1, "fitness": 0.7, "success_rate": 0.6, "last_used": 0},
            {"id": 2, "fitness": 0.6, "success_rate": 0.5, "last_used": 0},
            {"id": 3, "fitness": 0.9, "success_rate": 0.8, "last_used": 0},
        ]
        print(f"[LEARNING ENGINE] Initialized with {len(self.strategies)} default strategies")

    def get_strategies(self):
        return self.strategies

    def update_strategy(self, strategy_id, fitness=None, success_rate=None):
        for s in self.strategies:
            if s["id"] == strategy_id:
                if fitness is not None:
                    s["fitness"] = fitness
                if success_rate is not None:
                    s["success_rate"] = success_rate
                s["last_used"] = time.time()
                print(f"[LEARNING ENGINE] Updated Strategy {strategy_id} → fitness: {s['fitness']}, success_rate: {s['success_rate']}")
                break

# ⚡ Add this at the bottom to create a single shared instance
learning_engine = LearningEngine()