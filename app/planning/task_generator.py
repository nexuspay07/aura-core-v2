from typing import Dict, List


class TaskGenerator:
    """
    Converts a planning sequence into executable tasks.
    """

    def generate(
        self,
        plan: List[Dict],
    ) -> List[Dict]:

        tasks = []

        for task_id, step in enumerate(plan, start=1):

            tasks.append(
                {
                    "task_id": task_id,
                    "order": step["order"],
                    "name": step["step"],
                    "priority": step.get("priority", "normal"),
                    "status": "pending",
                    "completed": False,
                }
            )

        return tasks


task_generator = TaskGenerator()