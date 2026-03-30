# app/core/task_engine.py

class TaskEngine:
    def __init__(self):
        print("[TASK ENGINE] Initialized")

    def generate_tasks(self, goal, context, memories):
        # Normalize goal
        if isinstance(goal, str):
            goal = {"name": goal}
        elif not isinstance(goal, dict):
            goal = {"name": str(goal)}

        goal_name = goal.get("name", "unknown goal")

        tasks = [
            f"Analyze requirements for {goal_name}",
            f"Plan solution for {goal_name}",
            f"Execute improvements for {goal_name}",
            f"Evaluate results for {goal_name}"
        ]

        return tasks


task_engine = TaskEngine()