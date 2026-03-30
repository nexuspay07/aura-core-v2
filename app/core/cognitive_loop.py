# app/core/cognitive_loop.py

import asyncio
import json

from app.core.goal_engine import goal_engine
from app.core.context_engine import context_engine
from app.core.memory_retrieval_engine import memory_retrieval_engine
from app.core.task_engine import task_engine
from app.core.planning_engine import planning_engine

from app.learning.strategy_performance_tracker import strategy_performance_tracker
from app.learning.meta_strategy_engine import MetaStrategyEngine
from app.learning.self_learning_engine import self_learning_engine
from app.learning.adaptive_intelligence_engine import adaptive_intelligence_engine

from app.core.world_modeling_engine import world_modeling_engine
from app.core.multi_goal_engine import multi_goal_engine
from app.core.resource_intelligence_engine import resource_intelligence_engine

from app.core.autonomous_execution_engine import autonomous_execution_engine
from app.core.multi_agent_engine import Agent, multi_agent_engine

from app.security.identity_engine import identity_engine
from app.security.security_engine import security_engine

from app.monitoring.monitoring_engine import monitoring_engine
from app.control.control_engine import control_engine
from app.core.plan_optimizer_engine import plan_optimizer_engine
from app.lab.arbitration_engine import arbitration_engine

# 🔥 LAB SYSTEMS
from app.lab.simulation_engine import simulation_engine
from app.lab.world_engine import world_engine
from app.lab.debate_engine import debate_engine
from app.lab.agent_engine import agent_engine


# ==============================
# INIT META STRATEGY
# ==============================
meta_strategy_engine = MetaStrategyEngine(strategy_performance_tracker)


class CognitiveLoop:
    def __init__(self):

        # ==============================
        # MULTI-AGENT SYSTEM
        # ==============================
        multi_agent_engine.register_agent(Agent("Planner-1", "planner"))
        multi_agent_engine.register_agent(Agent("Executor-1", "executor"))
        multi_agent_engine.register_agent(Agent("Analyst-1", "analyst"))

        multi_agent_engine.register_agent(Agent("RiskAgent-1", "risk"))
        multi_agent_engine.register_agent(Agent("FinanceAgent-1", "finance"))
        multi_agent_engine.register_agent(Agent("MarketAgent-1", "market"))
        multi_agent_engine.register_agent(Agent("EthicsAgent-1", "ethics"))

        print("[MULTI-AGENT] Agents initialized")

        self.active_goal = None
        self.agent_token = security_engine.authenticate_agent("AURA_CORE")

        # WORLD MODEL
        world_modeling_engine.create_model(
            "business",
            {"demand": 100, "price": 10, "revenue": 1000, "cost": 500, "profit": 500},
            {"price": "affects demand"}
        )

        identity_engine.register_agent(
            "AURA_CORE",
            capabilities=["planning", "execution"]
        )

        print("[COGNITIVE LOOP] Initialized")

    # ==========================================
    # 🔥 LIVE SIMULATION (FIXED HUMAN CONTROL)
    # ==========================================
    async def run_simulation_stream(self, scenario):
        try:
            goal = scenario.get("goal", "Unknown Goal")

            yield f"Starting simulation for: {goal}\n"
            await asyncio.sleep(1)

            # 1. SIMULATION
            sim_result = simulation_engine.run_simulation(goal, scenario)
            yield "Strategies generated...\n"
            await asyncio.sleep(1)

            # 2. WORLD
            domain = world_engine.detect_domain(goal)
            world = world_engine.build_world(domain)

            yield f"World built: {domain}\n"
            await asyncio.sleep(1)

            sim_result["results"] = world_engine.apply_world(
                sim_result["results"], world
            )

            yield "World impact applied...\n"
            await asyncio.sleep(1)

            # 3. DEBATE
            debated, debates = debate_engine.run_debate(
                sim_result["results"], goal
            )

            sim_result["results"] = debated

            yield "Agents debating strategies...\n"
            await asyncio.sleep(1)

            # ==========================================
            # 🔥 ARBITRATION
            # ==========================================
            best, message = arbitration_engine.arbitrate(
                sim_result["results"],
                scenario
            )

            if best:
                sim_result["best_strategy"] = best
                yield f"Arbitration selected: {best['name']} (score: {round(best['final_score'],2)})\n"
            else:
                yield f"Arbitration failed: {message}\n"

            await asyncio.sleep(1)

            # ==========================================
            # 🔥 ✅ REAL HUMAN CONTROL (FIXED)
            # ==========================================
            yield "⚠️ Waiting for human approval...\n"

            # 🔥 BLOCK HERE UNTIL USER DECIDES
            decision = await asyncio.to_thread(control_engine.wait_for_decision)

            if decision == "rejected":
                yield "❌ Simulation rejected by user.\n"
                control_engine.reset()
                return

            yield "✅ Decision approved. Continuing execution...\n"
            control_engine.reset()

            await asyncio.sleep(1)

            # ==========================================
            # 4. AGENT EXECUTION
            # ==========================================
            steps = agent_engine.run_agents(sim_result)

            for step in steps:
                agent = step.get("agent", "System")
                message = step.get("message", "")
                status = step.get("status", "")

                yield f"[{agent}] {message} ({status})\n"
                await asyncio.sleep(1)

            yield "Simulation complete.\n"

        except Exception as e:
            yield f"Error: {str(e)}\n"

    # ==========================================
    # STANDARD LOOP
    # ==========================================
    def run(self):
        try:
            monitoring_engine.log_event("cognitive_loop_started")

            if not security_engine.verify_agent("AURA_CORE"):
                return {"status": "agent_not_authenticated"}

            new_goal = goal_engine.generate_goal()
            if new_goal:
                multi_goal_engine.add_goal(new_goal)

            goal = multi_goal_engine.get_next_goal()
            if not goal:
                return {"status": "no_goal"}

            goal = self._normalize_goal(goal)

            context = context_engine.collect_context()
            memories = memory_retrieval_engine.retrieve(context)

            tasks = task_engine.generate_tasks(goal, context, memories)
            plan = planning_engine.create_plan(tasks, context)

            resources = resource_intelligence_engine.get_current_resources()

            execution_results = autonomous_execution_engine.execute_plan(
                plan, {}, resources
            )

            return {
                "goal": goal,
                "execution_results": execution_results
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==========================================
    # HELPER
    # ==========================================
    @staticmethod
    def _normalize_goal(goal):
        if isinstance(goal, str):
            return {"name": goal}
        elif not isinstance(goal, dict):
            return {"name": str(goal)}
        return goal


# ✅ GLOBAL INSTANCE
cognitive_loop = CognitiveLoop()