# app/core/planning_engine.py

class PlanningEngine:

    def __init__(self):
        print("[PLANNING ENGINE] Initialized")

    def create_plan(self, tasks, context=None):
        plan = []

        for i, task in enumerate(tasks):

            # Handle both dict and string tasks
            if isinstance(task, dict):
                description = task.get("task", "No description")
            else:
                description = str(task)

            step = {
                "step_id": i + 1,
                "description": description,
                "status": "pending"
            }

            plan.append(step)

        print(f"[PLANNING ENGINE] Plan created with {len(plan)} steps")

        return plan


# Singleton
planning_engine = PlanningEngine()