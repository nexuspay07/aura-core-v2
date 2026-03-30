class KPITracker:

    def __init__(self):
        self.kpis = {
            "total_cycles": 0,
            "successful_decisions": 0,
            "failed_decisions": 0,
            "strategies_discovered": 0
        }

    def track(self, state):

        self.kpis["total_cycles"] += 1

        if state.get("success"):
            self.kpis["successful_decisions"] += 1
        else:
            self.kpis["failed_decisions"] += 1

        return self.kpis

    def track_strategy_discovered(self):
        self.kpis["strategies_discovered"] += 1


    # PHASE 180 — Adaptive Reward Intelligence
    def calculate_reward(self, kpis):

        successes = kpis["successful_decisions"]
        failures = kpis["failed_decisions"]
        cycles = kpis["total_cycles"]

        if cycles == 0:
            return 0

        success_rate = successes / cycles

        # Adaptive reward system
        if success_rate > 0.7:
            reward = 5
        elif success_rate > 0.4:
            reward = 10
        elif success_rate > 0.2:
            reward = 15
        else:
            reward = 20

        # Failure penalty scaling
        if failures > successes:
            reward -= 10

        return reward


kpi_tracker = KPITracker()