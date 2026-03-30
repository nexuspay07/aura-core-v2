import random
from datetime import datetime


class DecisionEngine:
    def __init__(self):
        self.decisions_made = 0
        self.last_decision_time = None

        print("[DECISION ENGINE] Initialized")

    def make_decision(self, goals, memories):
        """
        Decide which goal to prioritize based on memory and goals
        """

        if not goals:
            return None

        # Simple priority logic for now (will evolve later)
        selected_goal = self._select_goal(goals, memories)

        decision = {
            "decision_id": self.decisions_made + 1,
            "selected_goal": selected_goal,
            "decision_time": datetime.utcnow().isoformat(),
            "reason": "priority_selection"
        }

        self.decisions_made += 1
        self.last_decision_time = decision["decision_time"]

        print(f"[DECISION ENGINE] Decision #{self.decisions_made}: Selected goal")

        return decision

    def _select_goal(self, goals, memories):
        """
        Select goal using simple intelligence logic
        """

        # Example logic: prioritize newest goal
        if isinstance(goals, list) and len(goals) > 0:
            return goals[-1]

        return None

    def get_status(self):
        return {
            "decisions_made": self.decisions_made,
            "last_decision_time": self.last_decision_time
        }