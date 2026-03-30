# app/marketplace/strategy_engine.py

import datetime

class StrategyEngine:
    def __init__(self):
        self.strategies = []

    def save_strategy(self, username, strategy):
        strategy_id = len(self.strategies) + 1

        record = {
            "id": strategy_id,
            "creator": username,
            "name": strategy.get("name"),
            "logic": strategy,
            "rating": 0,
            "uses": 0,
            "created_at": str(datetime.datetime.utcnow())
        }

        self.strategies.append(record)

        return record

    def get_all(self):
        return sorted(self.strategies, key=lambda x: x["rating"], reverse=True)

    def use_strategy(self, strategy_id):
        for s in self.strategies:
            if s["id"] == strategy_id:
                s["uses"] += 1
                return s
        return None

    def rate_strategy(self, strategy_id, score):
        for s in self.strategies:
            if s["id"] == strategy_id:
                s["rating"] += score
                return s
        return None


strategy_engine = StrategyEngine()