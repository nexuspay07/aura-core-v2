# app/core/multi_agent_engine.py

class Agent:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def act(self, input_data):
        print(f"[AGENT:{self.name}] Acting as {self.role}")

        if self.role == "planner":
            return self.plan(input_data)

        elif self.role == "executor":
            return self.execute(input_data)

        elif self.role == "analyst":
            return self.analyze(input_data)

        return None

    def plan(self, goal):
        return [
            {"step_id": 1, "description": f"Analyze {goal['name']}", "status": "pending"},
            {"step_id": 2, "description": f"Design solution for {goal['name']}", "status": "pending"},
            {"step_id": 3, "description": f"Execute solution for {goal['name']}", "status": "pending"},
        ]

    def execute(self, step):
        return {
            "action": step,
            "status": "executed"
        }

    def analyze(self, results):
        return {
            "summary": "Execution successful",
            "steps_executed": len(results)
        }


class MultiAgentEngine:
    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(agent)

    def get_agent_by_role(self, role):
        for agent in self.agents:
            if agent.role == role:
                return agent
        return None

    def run(self, goal):
        print("[MULTI-AGENT] Running system")

        planner = self.get_agent_by_role("planner")
        executor = self.get_agent_by_role("executor")
        analyst = self.get_agent_by_role("analyst")

        # Step 1 — Plan
        plan = planner.act(goal)

        # Step 2 — Execute
        results = []
        for step in plan:
            result = executor.act(step)
            results.append(result)

        # Step 3 — Analyze
        analysis = analyst.act(results)

        return {
            "goal": goal,
            "plan": plan,
            "results": results,
            "analysis": analysis
        }


# GLOBAL INSTANCE
multi_agent_engine = MultiAgentEngine()