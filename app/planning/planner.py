from typing import Dict, List


class Planner:
    """
    Converts reasoning steps into an initial execution plan.
    """

    def create_plan(
        self,
        reasoning_steps: List[Dict],
    ) -> List[Dict]:

        plan = []

        for step in reasoning_steps:

            plan.append(
                {
                    "step": step["step"],
                    "order": step.get("order"),
                    "priority": "normal",
                    "status": "pending",
                }
            )

        return plan


planner = Planner()