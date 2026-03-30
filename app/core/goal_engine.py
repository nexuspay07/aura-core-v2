# app/core/goal_engine.py

import random


class GoalEngine:

    def __init__(self):
        print("[GOAL ENGINE] Initialized")

        self.goal_pool = [
            "Improve execution speed",
            "Optimize memory usage",
            "Enhance decision accuracy",
            "Analyze system performance",
            "Refine planning strategies"
        ]

    def generate_goal(self, name=None):

        if name is None:
            name = random.choice(self.goal_pool)

        goal = {
            "name": name,
            "priority": 1,
            "status": "active"
        }

        print(f"[GOAL ENGINE] New Goal Generated: {name}")

        return goal


goal_engine = GoalEngine()