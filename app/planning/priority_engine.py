from typing import Dict, List


class PriorityEngine:
    """
    Assigns execution priorities to tasks.

    Future versions may use:
    - Deadlines
    - User preferences
    - Learning Engine
    - Risk analysis
    - Business impact
    """

    PRIORITY_RULES = {
        "critical": [
            "emergency",
            "security",
            "payment",
            "fraud",
        ],
        "high": [
            "meeting",
            "email",
            "message",
            "customer",
        ],
        "normal": [],
    }

    def assign(
        self,
        tasks: List[Dict],
    ) -> List[Dict]:

        prioritized = []

        for task in tasks:

            task = task.copy()

            task["priority"] = self._determine_priority(
                task["name"]
            )

            prioritized.append(task)

        return prioritized

    def _determine_priority(
        self,
        task_name: str,
    ) -> str:

        task_lower = task_name.lower()

        for priority, keywords in self.PRIORITY_RULES.items():

            for keyword in keywords:

                if keyword in task_lower:
                    return priority

        return "normal"


priority_engine = PriorityEngine()