from typing import Any, Dict, List, Optional

from app.reasoning.goal_planner import goal_planner
from app.reasoning.thought_chain import thought_chain
from app.reasoning.executor import Executor


class ReasoningEngine:
    """
    Aura's reasoning pipeline.

    Goal
        ↓
    Goal Planner
        ↓
    Thought Chain
        ↓
    Executor
        ↓
    Results
    """

    def __init__(
        self,
        memory_engine=None,
        learning_engine=None,
    ):

        self.goal_planner = goal_planner
        self.thought_chain = thought_chain

        self.executor = Executor(
            memory_engine=memory_engine,
            learning_engine=learning_engine,
        )

    # ==========================================================
    # COMPLETE PIPELINE
    # ==========================================================

    def reason(
        self,
        goal: str,
    ) -> Dict[str, Any]:

        plan = self.goal_planner.plan(goal)

        evaluated_steps = self.thought_chain.evaluate(
            plan
        )

        execution = self.executor.run(
            evaluated_steps
        )

        success = all(
            step["success"]
            for step in execution
        )

        return {
            "goal": goal,
            "plan": plan,
            "evaluated_steps": evaluated_steps,
            "execution": execution,
            "success": success,
        }

    # ==========================================================
    # PLAN ONLY
    # ==========================================================

    def plan(
        self,
        goal: str,
    ) -> List[str]:

        return self.goal_planner.plan(goal)

    # ==========================================================
    # EVALUATE ONLY
    # ==========================================================

    def evaluate(
        self,
        steps: List[str],
    ) -> List[Dict]:

        return self.thought_chain.evaluate(
            steps
        )

    # ==========================================================
    # EXECUTE ONLY
    # ==========================================================

    def execute(
        self,
        evaluated_steps: List[Dict],
    ) -> List[Dict]:

        return self.executor.run(
            evaluated_steps
        )


reasoning_engine = ReasoningEngine()