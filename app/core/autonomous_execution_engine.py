# app/core/autonomous_execution_engine.py

import time


class AutonomousExecutionEngine:

    def __init__(self):
        self.execution_log = []

    def execute_plan(self, plan, world_state, resources):
        """
        Executes planned actions autonomously.
        """

        results = []

        for step in plan:

            # ✅ ALWAYS KEEP STRUCTURED DATA
            if isinstance(step, dict):
                action = step
            else:
                action = {"raw_step": step}

            print(f"[AUTONOMOUS EXECUTION] Executing action: {action}")

            result = self._execute_action(action)

            results.append(result)

        print("[AUTONOMOUS EXECUTION] Execution completed")

        return results

    def _execute_action(self, action):
        """
        Simulated execution layer.
        Later this will connect to:
        APIs, robots, IoT systems, databases.
        """

        # simulate delay
        time.sleep(0.1)

        # ✅ STORE REAL JSON (DICT), NOT STRING
        result = {
            "action": action,   # <-- now stays structured
            "status": "executed",
            "timestamp": time.time()
        }

        self.execution_log.append(result)

        return result


# global instance
autonomous_execution_engine = AutonomousExecutionEngine()