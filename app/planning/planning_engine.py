from typing import Any, Dict, List

from app.planning.planner import planner
from app.planning.task_generator import task_generator
from app.planning.priority_engine import priority_engine
from app.planning.dependency_resolver import dependency_resolver


class PlanningEngine:
    """
    Aura Planning Engine.

    Converts reasoning output into an execution-ready plan.

    Pipeline:

    Reasoning
        ↓
    Planner
        ↓
    Task Generator
        ↓
    Priority Engine
        ↓
    Dependency Resolver
        ↓
    Final Execution Plan
    """

    def __init__(self):

        self.planner = planner
        self.task_generator = task_generator
        self.priority_engine = priority_engine
        self.dependency_resolver = dependency_resolver

    # ==========================================================
    # COMPLETE PLANNING PIPELINE
    # ==========================================================

    def build_execution_plan(
        self,
        reasoning_steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        execution_plan = self.planner.create_plan(
            reasoning_steps
        )

        tasks = self.task_generator.generate(
            execution_plan
        )

        prioritized_tasks = self.priority_engine.assign(
            tasks
        )

        resolved_tasks = self.dependency_resolver.resolve(
            prioritized_tasks
        )

        return {
            "execution_plan": execution_plan,
            "tasks": resolved_tasks,
            "task_count": len(resolved_tasks),
            "ready_for_execution": True,
        }

    # ==========================================================
    # INDIVIDUAL PIPELINE STAGES
    # ==========================================================

    def create_plan(
        self,
        reasoning_steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.planner.create_plan(
            reasoning_steps
        )

    def generate_tasks(
        self,
        execution_plan: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.task_generator.generate(
            execution_plan
        )

    def prioritize_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.priority_engine.assign(
            tasks
        )

    def resolve_dependencies(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return self.dependency_resolver.resolve(
            tasks
        )


planning_engine = PlanningEngine()