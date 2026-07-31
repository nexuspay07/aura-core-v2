from typing import Any, Dict, List, Tuple

from app.execution.action_dispatcher import action_dispatcher


class ExecutionValidator:
    """
    Validates execution tasks before they are executed.

    Responsibilities:
    - Verify required fields
    - Verify task state
    - Verify dependencies
    - Verify action handlers
    """

    REQUIRED_FIELDS = [
        "task_id",
        "name",
        "status",
    ]

    # ==========================================================
    # SINGLE TASK
    # ==========================================================

    def validate(
        self,
        task: Dict[str, Any],
        completed_task_ids: List[int] | None = None,
    ) -> Tuple[bool, List[str]]:

        completed_task_ids = completed_task_ids or []

        errors = []

        # -----------------------------
        # Required fields
        # -----------------------------

        for field in self.REQUIRED_FIELDS:

            if field not in task:

                errors.append(
                    f"Missing required field '{field}'."
                )

        # -----------------------------
        # Status validation
        # -----------------------------

        status = task.get("status")

        if status not in (
            "pending",
            "running",
            "completed",
            "failed",
        ):

            errors.append(
                f"Invalid status '{status}'."
            )

        # -----------------------------
        # Dependency validation
        # -----------------------------

        dependency = task.get("depends_on")

        if (
            dependency is not None
            and dependency not in completed_task_ids
        ):

            errors.append(
                f"Dependency task {dependency} has not completed."
            )

        # -----------------------------
        # Action validation
        # -----------------------------

        action = task.get("action")

        if action:

            if not action_dispatcher.has_handler(action):

                errors.append(
                    f"No registered handler for action '{action}'."
                )

        return (
            len(errors) == 0,
            errors,
        )

    # ==========================================================
    # MULTIPLE TASKS
    # ==========================================================

    def validate_all(
        self,
        tasks: List[Dict[str, Any]],
        completed_task_ids: List[int] | None = None,
    ) -> Dict[str, Any]:

        completed_task_ids = completed_task_ids or []

        valid = []
        invalid = []

        for task in tasks:

            ok, errors = self.validate(
                task,
                completed_task_ids,
            )

            if ok:

                valid.append(task)

            else:

                invalid.append(
                    {
                        "task": task,
                        "errors": errors,
                    }
                )

        return {
            "valid_tasks": valid,
            "invalid_tasks": invalid,
            "all_valid": len(invalid) == 0,
        }


execution_validator = ExecutionValidator()