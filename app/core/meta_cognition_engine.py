# app/core/meta_cognition_engine.py

class MetaCognitionEngine:
    """
    Phase 209.4 — Meta-Cognition Engine
    Analyzes the cognitive loop after execution to provide self-awareness insights.
    """

    def __init__(self):
        # Initialize any internal memory or metrics storage
        self.loop_history = []

    def analyze_loop(self, goal, plan, long_horizon_plan, execution_results, strategy_id, world_state, resources, past_performance):
        """
        Analyze the cognitive loop for meta-cognitive insights.
        Returns a dictionary of insights.
        """

        # Normalize execution results if needed
        if isinstance(execution_results, list):
            exec_list = execution_results
        else:
            exec_list = [{"status": execution_results}]

        # Execution success ratio
        total_tasks = len(exec_list)
        completed_tasks = sum(1 for r in exec_list if r.get("status") == "completed")
        execution_success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        # Plan efficiency
        plan_efficiency = len(plan) / (len(long_horizon_plan) or 1)  # avoid division by zero

        # Resource utilization
        cpu_usage = resources.get("cpu", 0)
        memory_usage = resources.get("memory", 0)

        # Past strategy performance
        strategy_performance = past_performance.get(strategy_id, {"average_score": 0, "success_rate": 0})

        insights = {
            "goal_name": goal.get("name", "unknown"),
            "execution_success_rate": execution_success_rate,
            "plan_efficiency": plan_efficiency,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "strategy_average_score": strategy_performance.get("average_score", 0),
            "strategy_success_rate": strategy_performance.get("success_rate", 0),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks
        }

        # Store loop analysis for historical reference
        self.loop_history.append(insights)

        return insights

    def get_loop_history(self):
        """
        Returns the full history of meta-cognitive analyses.
        """
        return self.loop_history