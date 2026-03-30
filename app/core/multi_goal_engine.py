# app/core/multi_goal_engine.py

import heapq


class MultiGoalEngine:

    def __init__(self):
        self.goal_queue = []
        print("[MULTI GOAL ENGINE] Initialized")

    def add_goal(self, goal):

        if isinstance(goal, str):
            goal = {"name": goal}

        priority = goal.get("priority", 1)

        heapq.heappush(self.goal_queue, (-priority, goal))

        print(f"[MULTI GOAL ENGINE] Goal added: {goal['name']}")

    def get_next_goal(self):

        if not self.goal_queue:
            return None

        _, goal = heapq.heappop(self.goal_queue)

        print(f"[MULTI GOAL ENGINE] Next goal selected: {goal['name']}")

        return goal

    def get_all_goals(self):

        return [g for _, g in self.goal_queue]


multi_goal_engine = MultiGoalEngine()