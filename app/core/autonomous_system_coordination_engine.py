# app/core/autonomous_system_coordination_engine.py

import time


class AutonomousSystemCoordinationEngine:

    def __init__(self):

        self.systems = {}
        self.coordination_history = []

        print("[SYSTEM COORDINATION] Engine initialized")

    # -----------------------------------------
    # Register Subsystem
    # -----------------------------------------

    def register_system(self, name, priority=1):

        self.systems[name] = {
            "priority": priority,
            "last_execution": None,
            "status": "idle"
        }

        print(f"[SYSTEM COORDINATION] Registered system: {name}")

    # -----------------------------------------
    # Coordinate Systems
    # -----------------------------------------

    def coordinate(self, context):

        print("[SYSTEM COORDINATION] Coordinating subsystems...")

        execution_plan = []

        sorted_systems = sorted(
            self.systems.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )

        for system_name, system_data in sorted_systems:

            decision = self._evaluate_need(system_name, context)

            if decision:

                execution_plan.append(system_name)

                self.systems[system_name]["status"] = "scheduled"

        coordination_record = {
            "timestamp": time.time(),
            "context": context,
            "execution_plan": execution_plan
        }

        self.coordination_history.append(coordination_record)

        print("[SYSTEM COORDINATION] Execution plan:", execution_plan)

        return execution_plan

    # -----------------------------------------
    # Internal Decision Logic
    # -----------------------------------------

    def _evaluate_need(self, system_name, context):

        if "real_world_data" in context:
            return True

        if "resources" in context:
            return True

        return True

    # -----------------------------------------
    # Update System Status
    # -----------------------------------------

    def update_status(self, system_name, status):

        if system_name in self.systems:

            self.systems[system_name]["status"] = status
            self.systems[system_name]["last_execution"] = time.time()

            print(f"[SYSTEM COORDINATION] {system_name} status updated to {status}")

    # -----------------------------------------
    # Stats
    # -----------------------------------------

    def stats(self):

        return {
            "systems": len(self.systems),
            "coordination_cycles": len(self.coordination_history)
        }


autonomous_system_coordination_engine = AutonomousSystemCoordinationEngine()