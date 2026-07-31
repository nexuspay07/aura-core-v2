from typing import List


class GoalPlanner:
    """
    Breaks a high-level goal into sequential actionable steps.
    """

    def plan(
        self,
        goal: str,
    ) -> List[str]:
        """
        Generate a sequence of execution steps for a goal.
        """

        goal_lower = goal.lower()

        if "meeting" in goal_lower:
            return [
                "Check calendar availability",
                "Send meeting invitation",
                "Confirm meeting",
            ]

        if "summarize" in goal_lower:
            return [
                "Retrieve relevant memories",
                "Extract key points",
                "Generate summary",
            ]

        if "email" in goal_lower or "message" in goal_lower:
            return [
                "Draft message content",
                "Send message",
                "Log sent message in memory",
            ]

        return self._default_plan()

    def _default_plan(self) -> List[str]:
        """
        Fallback planning strategy.
        """

        return [
            "Analyze goal",
            "Break goal into micro-steps",
            "Execute micro-steps",
        ]


goal_planner = GoalPlanner()