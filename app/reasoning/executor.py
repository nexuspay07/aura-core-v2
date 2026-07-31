from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Executor:
    """
    Executes evaluated reasoning steps.

    External engines are optional and injected to keep
    this class independent of specific implementations.
    """

    def __init__(
        self,
        memory_engine=None,
        learning_engine=None,
    ):
        self.memory_engine = memory_engine
        self.learning_engine = learning_engine

    # ==========================================================
    # EXECUTION
    # ==========================================================

    def run(
        self,
        steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        results = []

        for step in steps:

            result = self._execute_step(step)

            results.append(result)

            self._post_execution(result)

        return results

    # ==========================================================
    # SINGLE STEP
    # ==========================================================

    def _execute_step(
        self,
        step: Dict[str, Any],
    ) -> Dict[str, Any]:

        confidence = step.get("confidence", 0.5)

        success = confidence >= 0.5

        return {
            "order": step.get("order"),
            "step": step["step"],
            "confidence": confidence,
            "status": "completed" if success else "failed",
            "success": success,
            "executed_at": datetime.now(timezone.utc),
        }

    # ==========================================================
    # POST EXECUTION
    # ==========================================================

    def _post_execution(
        self,
        result: Dict[str, Any],
    ) -> None:
        """
        Notify optional engines after execution.
        """

        if self.learning_engine:

            try:
                self.learning_engine.learn(result)
            except AttributeError:
                pass

        if self.memory_engine:

            try:
                self.memory_engine.record_execution(result)
            except AttributeError:
                pass


executor = Executor()