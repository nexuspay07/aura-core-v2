from typing import Any, Dict, List, Optional

from app.reasoning.reasoning_engine import ReasoningEngine


class ReasoningService:
    """
    Service layer for Aura's Reasoning subsystem.

    Responsibilities:
    - Expose reasoning capabilities to the application.
    - Orchestrate the ReasoningEngine.
    """

    def __init__(
        self,
        memory_engine=None,
        learning_engine=None,
    ):

        self.engine = ReasoningEngine(
            memory_engine=memory_engine,
            learning_engine=learning_engine,
        )

    # ==========================================================
    # COMPLETE REASONING
    # ==========================================================

    def reason(
        self,
        goal: str,
    ) -> Dict[str, Any]:

        return self.engine.reason(goal)

    # ==========================================================
    # PLAN ONLY
    # ==========================================================

    def plan(
        self,
        goal: str,
    ) -> List[str]:

        return self.engine.plan(goal)

    # ==========================================================
    # EVALUATE ONLY
    # ==========================================================

    def evaluate(
        self,
        steps: List[str],
    ) -> List[Dict[str, Any]]:

        return self.engine.evaluate(steps)

    # ==========================================================
    # EXECUTE ONLY
    # ==========================================================

    def execute(
        self,
        evaluated_steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.execute(evaluated_steps)


reasoning_service = ReasoningService()