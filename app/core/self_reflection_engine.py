from datetime import datetime


class SelfReflectionEngine:
    """
    Phase 41: Self Reflection Engine

    Allows AURA to:
    • Analyze reasoning results
    • Detect success/failure patterns
    • Store reflection memories
    • Improve future reasoning
    """

    def __init__(self, memory_engine):
        self.memory_engine = memory_engine

    # ==================================
    # REFLECT ON REASONING SESSION
    # ==================================

    def reflect_on_goal(self, goal: str, plan: list, results: list):

        successful_steps = 0
        failed_steps = 0

        for result in results:
            if result.get("success"):
                successful_steps += 1
            else:
                failed_steps += 1

        total_steps = len(results)

        if total_steps == 0:
            confidence_score = 0
        else:
            confidence_score = successful_steps / total_steps

        reflection = {
            "goal": goal,
            "success_rate": confidence_score,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "reflection_time": datetime.utcnow().isoformat(),
            "status": self._determine_status(confidence_score)
        }

        # Store reflection in memory
        self.memory_engine.store_memory(
            content=str(reflection),
            memory_type="self_reflection"
        )

        return reflection

    # ==================================
    # DETERMINE PERFORMANCE STATUS
    # ==================================

    def _determine_status(self, score):

        if score >= 0.9:
            return "excellent"

        elif score >= 0.7:
            return "good"

        elif score >= 0.5:
            return "moderate"

        else:
            return "needs_improvement"