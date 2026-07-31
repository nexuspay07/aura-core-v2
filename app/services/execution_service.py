from typing import Any, Dict, List

from app.execution.execution_engine import ExecutionEngine


class ExecutionService:
    """
    Service layer for Aura's Execution subsystem.

    Responsibilities:
    - Expose execution capabilities
    - Delegate orchestration to ExecutionEngine
    """

    def __init__(self):

        self.engine = ExecutionEngine()

    # ==========================================================
    # COMPLETE EXECUTION
    # ==========================================================

    def execute(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return self.engine.execute(tasks)

    # ==========================================================
    # VALIDATE ONLY
    # ==========================================================

    def validate(
        self,
        task: Dict[str, Any],
        completed_task_ids: List[int] | None = None,
    ):

        return self.engine.validator.validate(
            task,
            completed_task_ids,
        )

    # ==========================================================
    # PREPARE WORKFLOW
    # ==========================================================

    def prepare_workflow(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.workflow_manager.prepare(
            tasks
        )

    # ==========================================================
    # READY TASKS
    # ==========================================================

    def ready_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.workflow_manager.get_ready_tasks(
            tasks
        )

    # ==========================================================
    # EXECUTION METRICS
    # ==========================================================

    def metrics(
        self,
    ) -> Dict[str, Any]:

        return self.engine.monitor.metrics()

    # ==========================================================
    # EXECUTION HISTORY
    # ==========================================================

    def history(
        self,
    ) -> List[Dict[str, Any]]:

        return self.engine.monitor.history()

    # ==========================================================
    # CLEAR HISTORY
    # ==========================================================

    def clear_history(
        self,
    ) -> None:

        self.engine.monitor.clear()


execution_service = ExecutionService()