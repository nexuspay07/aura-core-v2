class PlanningEngine:

    def __init__(self):
        self.plan_count = 0

    def create_plan(self, goal):
        """
        Create structured execution plan from goal
        """

        self.plan_count += 1

        goal_text = goal.get("goal", "unknown goal")

        plan = {
            "plan_id": self.plan_count,
            "goal": goal_text,
            "steps": [
                f"analyze goal: {goal_text}",
                f"prepare execution strategy for: {goal_text}",
                f"execute goal: {goal_text}"
            ],
            "status": "created"
        }

        print(f"[PLANNING ENGINE] Created plan #{self.plan_count}")

        return plan