# app/core/execution_engine.py

import time


class ExecutionEngine:

    def __init__(self):
        pass

    def execute(self, plan):

        results = []

        # Ensure plan is iterable
        if not isinstance(plan, list):
            print("[EXECUTION ENGINE] Invalid plan format")
            return results

        for action in plan:

            # Determine action description safely
            description = None

            if isinstance(action, dict):
                description = (
                    action.get("description")
                    or action.get("task")
                    or action.get("action")
                )

            if not description:
                description = "No description"

            # Simulate execution
            result = {
                "task": description,
                "status": "completed",
                "timestamp": time.time()
            }

            print(f"[EXECUTION ENGINE] Executed action: {description}")

            results.append(result)

        print("[EXECUTION ENGINE] Execution completed")

        return results


# Global instance used by cognitive loop
execution_engine = ExecutionEngine()