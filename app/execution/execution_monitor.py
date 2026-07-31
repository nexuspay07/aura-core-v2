from datetime import datetime, timezone
from typing import Any, Dict, List


class ExecutionMonitor:
    """
    Monitors execution progress and records execution metrics.

    Future integrations:
    - Telemetry Service
    - Learning Service
    - Dashboard
    - Alerting
    """

    def __init__(self):

        self._history: List[Dict[str, Any]] = []

    # ==========================================================
    # RECORD
    # ==========================================================

    def record(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:

        record = {
            "task_id": task.get("task_id"),
            "task_name": task.get("name"),
            "success": result.get("success", False),
            "status": result.get("status"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "recorded_at": datetime.now(timezone.utc),
        }

        self._history.append(record)

        return record

    # ==========================================================
    # HISTORY
    # ==========================================================

    def history(self) -> List[Dict[str, Any]]:

        return list(self._history)

    # ==========================================================
    # METRICS
    # ==========================================================

    def metrics(self) -> Dict[str, Any]:

        total = len(self._history)

        successful = sum(
            1
            for item in self._history
            if item["success"]
        )

        failed = total - successful

        success_rate = (
            successful / total
            if total
            else 0.0
        )

        return {
            "total_tasks": total,
            "successful_tasks": successful,
            "failed_tasks": failed,
            "success_rate": round(success_rate, 2),
        }

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        self._history.clear()


execution_monitor = ExecutionMonitor()