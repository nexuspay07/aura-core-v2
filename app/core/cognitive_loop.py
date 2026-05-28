import asyncio
import json

from app.core.goal_engine import goal_engine
from app.core.context_engine import context_engine

from app.core.memory.memory_priority_retrieval_engine import (
    memory_priority_retrieval_engine
)

from app.memory.memory_retriever import (
    retrieve_relevant_memories
)

from app.core.task_engine import task_engine
from app.core.planning_engine import planning_engine

from app.learning.strategy_performance_tracker import (
    strategy_performance_tracker
)

from app.learning.meta_strategy_engine import (
    MetaStrategyEngine
)

from app.learning.self_learning_engine import (
    self_learning_engine
)

from app.learning.adaptive_intelligence_engine import (
    adaptive_intelligence_engine
)

from app.core.simulation.world_model_engine import (
    world_model_engine
)

from app.core.multi_goal_engine import (
    multi_goal_engine
)

from app.core.resource_intelligence_engine import (
    resource_intelligence_engine
)

from app.core.autonomous_execution_engine import (
    autonomous_execution_engine
)

from app.core.agents.multi_agent_engine import (
    multi_agent_engine,
    Agent
)

from app.security.identity_engine import (
    identity_engine
)

from app.security.security_engine import (
    security_engine
)

from app.monitoring.monitoring_engine import (
    monitoring_engine
)

from app.control.control_engine import (
    control_engine
)

from app.core.plan_optimizer_engine import (
    plan_optimizer_engine
)

from app.lab.simulation_engine import (
    simulation_engine
)

from app.lab.world_engine import (
    world_engine
)

from app.lab.debate_engine import (
    debate_engine
)

from app.lab.agent_engine import (
    agent_engine
)

from app.lab.failure_engine import (
    failure_engine
)

from app.core.operational_intelligence_engine import (
    operational_intelligence_engine
)

from app.core.simulation.strategic_simulation_engine import (
    strategic_simulation_engine
)

from app.core.business_understanding_engine import (
    business_understanding_engine
)

from app.core.reasoning.dynamic_reasoning_engine import (
    dynamic_reasoning_engine
)

from app.core.market.market_intelligence_engine import (
    market_intelligence_engine
)

from app.core.strategy_comparison_engine import (
    strategy_comparison_engine
)

from app.core.simulation.prediction_engine import (
    prediction_engine
)

from app.core.visual_intelligence_engine import (
    visual_intelligence_engine
)

from app.core.decision_memory_engine import (
    decision_memory_engine
)

from app.core.strategy_reinforcement_engine import (
    strategy_reinforcement_engine
)


meta_strategy_engine = MetaStrategyEngine(
    strategy_performance_tracker
)


class CognitiveLoop:

    def __init__(self):

        multi_agent_engine.register_agent(
            Agent("Planner-1", "planner")
        )

        multi_agent_engine.register_agent(
            Agent("Executor-1", "executor")
        )

        multi_agent_engine.register_agent(
            Agent("Analyst-1", "analyst")
        )

        multi_agent_engine.register_agent(
            Agent("RiskAgent-1", "risk")
        )

        multi_agent_engine.register_agent(
            Agent("FinanceAgent-1", "finance")
        )

        multi_agent_engine.register_agent(
            Agent("MarketAgent-1", "market")
        )

        multi_agent_engine.register_agent(
            Agent("EthicsAgent-1", "ethics")
        )

        print("[MULTI-AGENT] Agents initialized")

        self.agent_token = security_engine.authenticate_agent(
            "AURA_CORE"
        )

        world_model_engine.create_model(
            "business",
            {
                "demand": 100,
                "price": 10,
                "revenue": 1000,
                "cost": 500,
                "profit": 500
            },
            {
                "price": "affects demand"
            }
        )

        identity_engine.register_agent(
            "AURA_CORE",
            capabilities=["planning", "execution"]
        )

        print("[COGNITIVE LOOP] Initialized")

    @staticmethod
    def _stream_event(step, message, data=None):

        return json.dumps({
            "step": step,
            "message": message,
            "data": data
        }) + "\n"

    def run_intelligence_pipeline(
        self,
        goal: str,
        scenario: dict,
        profile: dict | None = None
    ):

        try:

            profile = profile or {}

            business_understanding = (
                business_understanding_engine.analyze(
                    goal,
                    scenario
                )
            )

            business_dna = business_understanding.get(
                "business_dna",
                {}
            )

            dynamic_reasoning = (
                dynamic_reasoning_engine.analyze(
                    business_dna
                )
            )

            market_intelligence = (
                market_intelligence_engine.analyze(
                    business_dna.get(
                        "business_model",
                        "general_business"
                    ),
                    scenario
                )
            )

            sim_result = simulation_engine.run_simulation(
                goal,
                scenario
            )

            domain = world_engine.detect_domain(goal)

            world = world_engine.build_world(domain)

            world.update(scenario)

            sim_result["results"] = (
                world_engine.apply_world(
                    sim_result.get("results", []),
                    world
                )
            )

            debated_results, debates = (
                debate_engine.run_debate(
                    sim_result["results"],
                    goal
                )
            )

            sim_result["results"] = debated_results

            failures = failure_engine.predict(
                sim_result["results"],
                scenario,
                world
            )

            for s in sim_result["results"]:

                if "final_score" not in s:
                    s["final_score"] = s.get("score", 0)

                failure_data = next(
                    (
                        f for f in failures
                        if f.get("strategy") == s.get("name")
                    ),
                    None
                )

                failure_prob = (
                    failure_data["failure_probability"] / 100
                    if failure_data else 0.3
                )

                base_conf = s.get("confidence", 0.7)

                adjusted_conf = (
                    base_conf * (1 - failure_prob)
                )

                trust_score = (
                    adjusted_conf
                    * s.get("final_score", 1)
                )

                s["confidence_score"] = round(
                    adjusted_conf * 100,
                    2
                )

                s["trust_score"] = round(
                    trust_score,
                    2
                )

                s["failure_probability"] = round(
                    failure_prob * 100,
                    2
                )

                score = s.get("final_score", 0)

                s["decision_score"] = round(
                    score - (
                        s["failure_probability"] * 0.05
                    ),
                    2
                )

            sim_result["results"] = sorted(
                sim_result["results"],
                key=lambda x: x.get(
                    "decision_score",
                    0
                ),
                reverse=True
            )

            best = (
                sim_result["results"][0]
                if sim_result.get("results")
                else {}
            )

            sim_result["best_strategy"] = best

            strategy_comparison = (
                strategy_comparison_engine.compare(
                    business_dna.get(
                        "business_model",
                        "general_business"
                    ),
                    scenario
                )
            )

            prediction = (
                prediction_engine.predict_outcome(
                    business_dna.get(
                        "business_model",
                        "general_business"
                    ),
                    best.get("name", "Balanced"),
                    scenario
                )
            )

            visual_intelligence = (
                visual_intelligence_engine.analyze({
                    "confidence": prediction.get(
                        "confidence",
                        0.65
                    ),
                    "main_risk": dynamic_reasoning.get(
                        "strategic_warning",
                        ""
                    ),
                    "market_pressure": market_intelligence.get(
                        "market_pressure",
                        ""
                    )
                })
            )

            strategic_simulation = (
                strategic_simulation_engine.simulate(
                    goal,
                    business_dna,
                    dynamic_reasoning,
                    prediction
                )
            )

            operational_intelligence = (
                operational_intelligence_engine.analyze(
                    goal,
                    business_dna,
                    dynamic_reasoning,
                    strategic_simulation
                )
            )

            # ==========================================
            # DECISION MEMORY
            # ==========================================

            decision_memory = (
                decision_memory_engine.save_decision(
                    goal=goal,
                    business_dna=business_dna,
                    dynamic_reasoning=dynamic_reasoning,
                    prediction=prediction,
                    simulation=sim_result,
                    operational_intelligence=operational_intelligence
                )
            )

            memory_summary = (
                decision_memory_engine.summarize_history()
            )

            # ==========================================
            # STRATEGY REINFORCEMENT
            # ==========================================

            strategy_reinforcement = (
                strategy_reinforcement_engine.analyze(
                    memory_summary,
                    strategic_simulation
                )
            )

            return {
                "status": "success",
                "goal": goal,
                "scenario": scenario,
                "profile": profile,
                "business_understanding": business_understanding,
                "business_dna": business_dna,
                "dynamic_reasoning": dynamic_reasoning,
                "market_intelligence": market_intelligence,
                "strategy_comparison": strategy_comparison,
                "prediction": prediction,
                "visual_intelligence": visual_intelligence,
                "strategic_simulation": strategic_simulation,
                "operational_intelligence": operational_intelligence,
                "simulation": sim_result,
                "results": sim_result.get("results", []),
                "best_strategy": best,
                "failures": failures,
                "debates": debates,
                "decision_memory": decision_memory,
                "memory_summary": memory_summary,
                "strategy_reinforcement": strategy_reinforcement,
                "world": world
            }

        except Exception as e:

            return {
                "status": "error",
                "message": str(e),
                "goal": goal,
                "scenario": scenario
            }

    def run(self):

        try:

            monitoring_engine.log_event(
                "cognitive_loop_started"
            )

            if not security_engine.verify_agent(
                "AURA_CORE"
            ):

                return {
                    "status": "agent_not_authenticated"
                }

            goal = multi_goal_engine.get_next_goal()

            if not goal:

                return {
                    "status": "no_goal"
                }

            goal = self._normalize_goal(goal)

            context = context_engine.collect_context()

            # ==========================================
            # SEMANTIC MEMORY RETRIEVAL
            # ==========================================

            raw_memories = asyncio.run(
                retrieve_relevant_memories(
                    tenant_id="AURA_SYSTEM",
                    domain="general",
                    query=str(context),
                    limit=10
                )
            )

            memory_objects = []

            for memory in raw_memories:

                if isinstance(memory, dict):

                    memory_objects.append({
                        "memory": memory.get(
                            "text",
                            str(memory)
                        ),
                        "importance_score": memory.get(
                            "importance_score",
                            10
                        ),
                        "semantic_score": memory.get(
                            "score",
                            0.5
                        ),
                        "reinforcement_strength": memory.get(
                            "reinforcement_strength",
                            1.0
                        ),
                        "confidence": memory.get(
                            "confidence",
                            0.5
                        ),
                        "recall_count": memory.get(
                            "recall_count",
                            1
                        ),
                        "decay_factor": memory.get(
                            "decay_factor",
                            1.0
                        )
                    })

                else:

                    memory_objects.append({
                        "memory": str(memory),
                        "importance_score": 10,
                        "semantic_score": 0.5,
                        "reinforcement_strength": 1.0,
                        "confidence": 0.5,
                        "recall_count": 1,
                        "decay_factor": 1.0
                    })

            memories = (
                memory_priority_retrieval_engine
                .retrieve_priority_memories(
                    memory_objects
                )
            )

            # ==========================================
            # TASK GENERATION
            # ==========================================

            tasks = task_engine.generate_tasks(
                goal,
                context,
                memories
            )

            # ==========================================
            # PLANNING
            # ==========================================

            plan = planning_engine.create_plan(
                tasks,
                context
            )

            # ==========================================
            # RESOURCE ANALYSIS
            # ==========================================

            resources = (
                resource_intelligence_engine
                .get_current_resources()
            )

            # ==========================================
            # EXECUTION
            # ==========================================

            execution_results = (
                autonomous_execution_engine
                .execute_plan(
                    plan,
                    {},
                    resources
                )
            )

            return {
                "goal": goal,
                "context": context,
                "memories_used": memories,
                "tasks": tasks,
                "plan": plan,
                "resources": resources,
                "execution_results": execution_results
            }

        except Exception as e:

            return {
                "status": "error",
                "message": str(e)
            }

    @staticmethod
    def _normalize_goal(goal):

        if isinstance(goal, str):
            return {"name": goal}

        elif not isinstance(goal, dict):
            return {"name": str(goal)}

        return goal


cognitive_loop = CognitiveLoop()