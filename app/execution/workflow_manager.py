from typing import Any, Dict, List


class WorkflowManager:
    """
    Coordinates task execution workflows.

    Responsible for:
    - Ordering tasks
    - Checking dependencies
    - Determining which tasks are ready
    """

    def prepare(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Sort tasks into execution order.
        """

        return sorted(
            tasks,
            key=lambda task: task.get("order", 0),
        )

    def get_ready_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Return tasks whose dependencies have been satisfied.
        """

        completed = {
            task["task_id"]
            for task in tasks
            if task.get("status") == "completed"
        }

        ready = []

        for task in tasks:

            if task.get("status") == "completed":
                continue

            dependency = task.get("depends_on")

            if dependency is None or dependency in completed:
                ready.append(task)

        return ready

    def is_complete(
        self,
        tasks: List[Dict[str, Any]],
    ) -> bool:
        """
        Determine whether the workflow has finished.
        """

        return all(
            task.get("status") == "completed"
            for task in tasks
        )


workflow_manager = WorkflowManager()