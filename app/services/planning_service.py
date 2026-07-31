from typing import Any, Dict, List

from app.planning.planning_engine import PlanningEngine


class PlanningService:
    """
    Service layer for Aura's Planning subsystem.

    Responsibilities:
    - Expose planning capabilities to the application.
    - Delegate orchestration to the PlanningEngine.
    """

    def __init__(self):

        self.engine = PlanningEngine()

    # ==========================================================
    # COMPLETE PLANNING PIPELINE
    # ==========================================================

    def build_execution_plan(
        self,
        reasoning_steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return self.engine.build_execution_plan(
            reasoning_steps
        )

    # ==========================================================
    # PLAN ONLY
    # ==========================================================

    def create_plan(
        self,
        reasoning_steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.create_plan(
            reasoning_steps
        )

    # ==========================================================
    # TASK GENERATION
    # ==========================================================

    def generate_tasks(
        self,
        execution_plan: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.generate_tasks(
            execution_plan
        )

    # ==========================================================
    # PRIORITIZATION
    # ==========================================================

    def prioritize_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.prioritize_tasks(
            tasks
        )

    # ==========================================================
    # DEPENDENCY RESOLUTION
    # ==========================================================

    def resolve_dependencies(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.engine.resolve_dependencies(
            tasks
        )


planning_service = PlanningService()