# app/core/knowledge_abstraction_engine.py

class KnowledgeAbstractionEngine:

    def __init__(self):
        self.knowledge_base = []

    def abstract_knowledge(self, loop_data):
        """
        Generates higher-level knowledge from cognitive loop execution data.
        loop_data: dict containing goals, plans, execution results, metrics
        Returns a summary abstraction.
        """
        goal_name = loop_data.get("goal", {}).get("name", "unknown_goal")
        score = loop_data.get("score", 0)
        plan_steps = loop_data.get("plan", [])
        long_horizon_steps = loop_data.get("long_horizon_plan", [])
        resources = loop_data.get("resources", {})
        global_insights = loop_data.get("global_insights", {})

        abstraction = {
            "goal_name": goal_name,
            "success": score >= 0.8,
            "plan_length": len(plan_steps),
            "long_horizon_plan_length": len(long_horizon_steps),
            "resource_efficiency": resources.get("cpu", 0) / max(1, len(plan_steps)),
            "strategy_insights": global_insights.get("meta_strategy", []),
            "world_state_summary": global_insights.get("world_state", {}),
        }

        self.knowledge_base.append(abstraction)
        return abstraction

    def get_knowledge(self):
        return self.knowledge_base