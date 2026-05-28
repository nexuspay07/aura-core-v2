# app/reasoning/reasoning_engine.py

from app.reasoning.goal_planner import GoalPlanner
from app.reasoning.thought_chain import ThoughtChain
from app.reasoning.executor import Executor

class ReasoningEngine:
    def __init__(self, memory_engine=None, learning_engine=None):
        self.goal_planner = GoalPlanner()
        self.thought_chain = ThoughtChain()
        self.executor = Executor(memory_engine, learning_engine)

    def achieve_goal(self, goal: str):
        # Step 1: Plan
        steps = self.goal_planner.plan(goal)

        # Step 2: Evaluate
        evaluated_steps = self.thought_chain.evaluate(steps)

        # Step 3: Execute
        results = self.executor.run(evaluated_steps)

        return {
            "goal": goal,
            "steps": evaluated_steps,
            "results": results
        }