from typing import Any, Dict, List

from app.execution.workflow_manager import workflow_manager
from app.execution.execution_validator import execution_validator
from app.execution.task_executor import task_executor
from app.execution.action_dispatcher import action_dispatcher
from app.execution.execution_monitor import execution_monitor


class ExecutionEngine:
    """
    Aura Execution Engine.

    Coordinates the complete execution pipeline.

    Planning
        ↓
    Workflow Manager
        ↓
    Execution Validator
        ↓
    Task Executor
        ↓
    Action Dispatcher
        ↓
    Execution Monitor
    """

    def __init__(self):

        self.workflow_manager = workflow_manager
        self.validator = execution_validator
        self.executor = task_executor
        self.dispatcher = action_dispatcher
        self.monitor = execution_monitor

    # ==========================================================
    # COMPLETE EXECUTION PIPELINE
    # ==========================================================

    def execute(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        ordered_tasks = self.workflow_manager.prepare(tasks)

        completed_task_ids: List[int] = []
        execution_results = []

        while True:

            ready_tasks = self.workflow_manager.get_ready_tasks(
                ordered_tasks
            )

            if not ready_tasks:
                break

            progress = False

            for task in ready_tasks:

                valid, errors = self.validator.validate(
                    task,
                    completed_task_ids,
                )

                if not valid:

                    execution_results.append(
                        {
                            "task": task,
                            "success": False,
                            "status": "failed_validation",
                            "errors": errors,
                        }
                    )

                    task["status"] = "failed"

                    continue

                dispatch_result = None

                if task.get("action"):

                    dispatch_result = self.dispatcher.dispatch(task)

                    if not dispatch_result.get("success", False):

                        execution_results.append(
                            {
                                "task": task,
                                "success": False,
                                "status": "dispatch_failed",
                                "dispatch": dispatch_result,
                            }
                        )

                        task["status"] = "failed"

                        continue

                result = self.executor.execute_task(task)

                task["status"] = result["status"]

                if result["success"]:

                    completed_task_ids.append(
                        task["task_id"]
                    )

                self.monitor.record(
                    task,
                    result,
                )

                execution_results.append(result)

                progress = True

            if not progress:
                break

        metrics = self.monitor.metrics()

        return {
            "results": execution_results,
            "completed_tasks": completed_task_ids,
            "workflow_complete": self.workflow_manager.is_complete(
                ordered_tasks
            ),
            "metrics": metrics,
        }


execution_engine = ExecutionEngine()