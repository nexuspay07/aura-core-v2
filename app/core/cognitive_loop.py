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

# 🔥 LAB SYSTEMS
from app.lab.simulation_engine import simulation_engine
from app.lab.world_engine import world_engine
from app.lab.debate_engine import debate_engine
from app.lab.agent_engine import agent_engine
from app.lab.failure_engine import failure_engine


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

        self.agent_token = security_engine.authenticate_agent("AURA_CORE")

        # ==============================
        # WORLD MODEL
        # ==============================
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
    # STREAM HELPER
    # ==========================================
    @staticmethod
    def _stream_event(step, message, data=None) -> str:
        return json.dumps({
            "step": step,
            "message": message,
            "data": data
        }) + "\n"

    # ==========================================
    # 🔥 STRUCTURED LIVE STREAM
    # ==========================================
    async def run_simulation_stream(self, scenario):
        try:
            goal = scenario.get("goal", "Unknown Goal")

            yield self._stream_event(
                "start",
                f"Starting AURA simulation for: {goal}"
            )
            await asyncio.sleep(0.5)

            # ==========================
            # 1. SIMULATION
            # ==========================
            sim_result = simulation_engine.run_simulation(goal, scenario)

            yield self._stream_event(
                "simulation",
                "Strategies generated",
                {"count": len(sim_result.get("results", []))}
            )

            # ==========================
            # 2. WORLD MODELING
            # ==========================
            domain = world_engine.detect_domain(goal)
            world = world_engine.build_world(domain)

            # Keep stream logic aligned with /lab/simulate
            world["risk_tolerance"] = scenario.get("risk_tolerance", 0.5)
            world["budget"] = scenario.get("budget", 10000)
            world["market"] = scenario.get("market", "normal")

            sim_result["results"] = world_engine.apply_world(
                sim_result.get("results", []),
                world
            )

            yield self._stream_event(
                "world",
                f"World applied: {domain}",
                world
            )

            # ==========================
            # 3. DEBATE SYSTEM
            # ==========================
            debated, debates = debate_engine.run_debate(
                sim_result["results"],
                goal
            )
            sim_result["results"] = debated

            yield self._stream_event(
                "debate",
                "Strategies debated",
                {"count": len(debates)}
            )

            # ==========================
            # 4. FAILURE PREDICTION
            # ==========================
            failures = failure_engine.predict(
                sim_result["results"],
                scenario,
                world
            )

            yield self._stream_event(
                "failure",
                "Failure analysis complete",
                failures
            )

            # ==========================
            # 5. TRUST SCORING
            # ==========================
            for s in sim_result["results"]:
                if "final_score" not in s:
                    s["final_score"] = s.get("score", 0)

                base_conf = s.get("confidence", 0.7)

                failure_data = next(
                    (f for f in failures if f["strategy"] == s["name"]),
                    None
                )

                failure_prob = (
                    failure_data["failure_probability"] / 100
                    if failure_data else 0.3
                )

                adjusted_conf = base_conf * (1 - failure_prob)
                trust_score = adjusted_conf * s.get("final_score", 1)

                s["confidence_score"] = round(adjusted_conf * 100, 2)
                s["trust_score"] = round(trust_score, 2)
                s["failure_probability"] = round(failure_prob * 100, 2)

            yield self._stream_event(
                "trust",
                "Trust scoring complete",
                sim_result["results"]
            )

            # ==========================
            # 6. FINAL DECISION (UNIFIED)
            # ==========================
            for s in sim_result["results"]:
                score = s.get("final_score", 0)
                failure = s.get("failure_probability", 0)
                s["decision_score"] = round(score - (failure * 0.05), 2)

            sim_result["results"] = sorted(
                sim_result["results"],
                key=lambda x: x["decision_score"],
                reverse=True
            )

            best = sim_result["results"][0]
            sim_result["best_strategy"] = best

            yield self._stream_event(
                "decision",
                f"Best strategy selected: {best['name']}",
                best
            )

            # ==========================
            # 7. HUMAN CONTROL
            # ==========================
            yield self._stream_event(
                "waiting",
                "Awaiting human approval"
            )

            decision = await asyncio.to_thread(control_engine.wait_for_decision)

            if decision == "rejected":
                yield self._stream_event(
                    "rejected",
                    "Simulation rejected by user"
                )
                control_engine.reset()
                return

            yield self._stream_event(
                "approved",
                "Approved. Executing"
            )
            control_engine.reset()

            # ==========================
            # 8. AGENT EXECUTION
            # ==========================
            steps = agent_engine.run_agents(sim_result)

            for step in steps:
                yield self._stream_event(
                    "agent",
                    step.get("message", ""),
                    step
                )
                await asyncio.sleep(0.3)

            # ==========================
            # 9. SELF LEARNING
            # ==========================
            try:
                self_learning_engine.learn_from_execution(goal, sim_result)
            except Exception as learning_error:
                yield self._stream_event(
                    "warning",
                    f"Learning update failed: {str(learning_error)}"
                )

            yield self._stream_event(
                "complete",
                "Simulation complete",
                {
                    "best_strategy": sim_result.get("best_strategy"),
                    "results_count": len(sim_result.get("results", []))
                }
            )

        except Exception as e:
            yield self._stream_event("error", str(e))

    # ==========================================
    # STANDARD LOOP
    # ==========================================
    def run(self):
        try:
            monitoring_engine.log_event("cognitive_loop_started")

            if not security_engine.verify_agent("AURA_CORE"):
                return {"status": "agent_not_authenticated"}

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