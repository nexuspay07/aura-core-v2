from typing import Dict

from app.services.telemetry_service import telemetry_service


class KPIService:
    """
    Centralized KPI service for Aura.

    Responsible for:

    • Executive dashboard metrics
    • AI execution statistics
    • Reward calculation
    • Business intelligence KPIs

    Future versions can calculate KPIs directly from
    telemetry logs instead of relying on in-memory values.
    """

    def __init__(self):

        self.kpis = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "strategies_discovered": 0,
            "average_latency_ms": 0,
            "tokens_used": 0,
        }

    # ==========================================================
    # EXECUTION TRACKING
    # ==========================================================

    def record_execution(
        self,
        success: bool,
        latency_ms: int = 0,
        tokens_used: int = 0,
    ) -> Dict:

        self.kpis["total_requests"] += 1

        if success:
            self.kpis["successful_requests"] += 1
        else:
            self.kpis["failed_requests"] += 1

        self.kpis["tokens_used"] += tokens_used

        total = self.kpis["total_requests"]

        previous_average = self.kpis["average_latency_ms"]

        self.kpis["average_latency_ms"] = int(
            ((previous_average * (total - 1)) + latency_ms) / total
        )

        return self.kpis

    # ==========================================================
    # STRATEGY DISCOVERY
    # ==========================================================

    def record_strategy_discovered(self):

        self.kpis["strategies_discovered"] += 1

    # ==========================================================
    # KPI SUMMARY
    # ==========================================================

    def get_summary(self):

        total = self.kpis["total_requests"]

        if total == 0:
            success_rate = 0
        else:
            success_rate = round(
                self.kpis["successful_requests"] / total * 100,
                2,
            )

        return {
            **self.kpis,
            "success_rate": success_rate,
        }

    # ==========================================================
    # ADAPTIVE REWARD ENGINE
    # ==========================================================

    def calculate_reward(self):

        summary = self.get_summary()

        rate = summary["success_rate"]

        if rate >= 90:
            reward = 100

        elif rate >= 75:
            reward = 75

        elif rate >= 50:
            reward = 50

        else:
            reward = 25

        if summary["failed_requests"] > summary["successful_requests"]:
            reward = max(reward - 15, 0)

        return reward


kpi_service = KPIService()