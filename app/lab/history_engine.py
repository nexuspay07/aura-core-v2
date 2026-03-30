# app/lab/history_engine.py

import datetime

class HistoryEngine:
    def __init__(self):
        self.storage = {}

    async def save(self, username, data):
        if username not in self.storage:
            self.storage[username] = []

        sim_id = len(self.storage[username]) + 1

        record = {
            "id": sim_id,
            "timestamp": str(datetime.datetime.utcnow()),
            "goal": data["goal"],
            "scenario": data["scenario"],
            "result": data["result"]
        }

        self.storage[username].append(record)

    async def get(self, username):
        return self.storage.get(username, [])

    async def analyze_patterns(self, username):
        history = self.storage.get(username, [])

        patterns = {}

        for sim in history:
            best = sim["result"].get("best_strategy", {})
            name = best.get("name")

            if name:
                patterns[name] = patterns.get(name, 0) + 1

        return patterns


history_engine = HistoryEngine()