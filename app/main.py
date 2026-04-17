from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="AURA AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.db.database import database, engine, metadata
from app.lab.world_engine import world_engine
from app.lab.history_engine import history_engine
from app.lab.learning_engine import learning_engine
from app.lab.failure_engine import failure_engine
from app.core.cognitive_loop import cognitive_loop
from app.control.control_engine import control_engine
from app.lab.simulation_engine import simulation_engine
from app.lab.explanation_engine import explanation_engine
from app.lab.agent_engine import agent_engine
from app.lab.debate_engine import debate_engine

from app.api.strategy_routes import router as strategy_router
from app.api.marketplace_routes import router as marketplace_router
from app.core.conversation_engine import conversation_engine

app.include_router(strategy_router)
app.include_router(marketplace_router)


def generate_action_plan(strategy):
    name = strategy.get("name", "Balanced")

    if name == "Aggressive":
        return [
            "Launch MVP immediately",
            "Invest heavily in user acquisition",
            "Prioritize rapid scaling over stability",
            "Capture market share before competitors react"
        ]

    elif name == "Balanced":
        return [
            "Validate product-market fit",
            "Scale gradually with controlled spending",
            "Optimize operations while growing",
            "Monitor competition closely"
        ]

    else:  # Conservative
        return [
            "Minimize costs and protect capital",
            "Test market with small experiments",
            "Focus on stable revenue streams",
            "Scale only after proven success"
        ]


@app.on_event("startup")
async def startup():
    metadata.create_all(engine)
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


class SimulationRequest(BaseModel):
    goal: str
    risk_tolerance: float = 0.5
    budget: int = 10000
    market: str = "normal"

class ConversationRequest(BaseModel):
    message: str    


@app.post("/lab/simulate")
async def simulate(data: SimulationRequest):
    scenario = data.dict()
    goal = scenario.get("goal")



    if not goal or goal.strip() == "":
        return {"error": "Goal is required"}

    username = "test_user"

    sim_result = simulation_engine.run_simulation(goal, scenario)

    domain = world_engine.detect_domain(goal)
    world = world_engine.build_world(domain)

    world["risk_tolerance"] = scenario["risk_tolerance"]
    world["budget"] = scenario["budget"]
    world["market"] = scenario["market"]

    sim_result["results"] = world_engine.apply_world(
        sim_result.get("results", []), world
    )

    patterns = await learning_engine.learn(username, history_engine)

    sim_result["results"] = learning_engine.apply_learning(
        sim_result["results"],
        scenario,
        patterns
    )

    debated_strategies, debates = debate_engine.run_debate(
        sim_result["results"], goal
    )
    sim_result["results"] = debated_strategies

    agent_steps = agent_engine.run_agents(sim_result)

    failures = failure_engine.predict(
        sim_result["results"],
        scenario,
        world
    )

    for s in sim_result["results"]:
        if "final_score" not in s:
            s["final_score"] = s.get("score", 0)

        failure_data = next(
            (f for f in failures if f["strategy"] == s["name"]),
            None
        )

        failure_prob = (
            failure_data["failure_probability"] / 100
            if failure_data else 0.3
        )

        base_conf = s.get("confidence", 0.7)
        adjusted_conf = base_conf * (1 - failure_prob)
        trust_score = adjusted_conf * s.get("final_score", 1)

        s["confidence_score"] = round(adjusted_conf * 100, 2)
        s["trust_score"] = round(trust_score, 2)
        s["failure_probability"] = round(failure_prob * 100, 2)
        s["decision_score"] = round(
            s.get("final_score", 0) - (failure_prob * 5),
            2
        )

        # ✅ PREDICTED OUTCOME
        s["outcome"] = {
            "reward": "high" if s.get("score", 0) > 2 else "medium",
            "risk": s.get("risk", "unknown"),
            "timeframe": "short-term" if s.get("risk") == "high" else "long-term"
        }

    sim_result["results"] = sorted(
        sim_result["results"],
        key=lambda x: x["decision_score"],
        reverse=True
    )

    best = sim_result["results"][0]
    best["action_plan"] = generate_action_plan(best)

    second_best = sim_result["results"][1] if len(sim_result["results"]) > 1 else None
    if second_best:
        second_best["action_plan"] = generate_action_plan(second_best)

    sim_result["best_strategy"] = best
    sim_result["alternative_strategy"] = second_best

    explanation = explanation_engine.generate(
        best,
        sim_result["results"],
        failures=failures,
        world=world
    )

    await history_engine.save(username, {
        "goal": goal,
        "scenario": scenario,
        "result": sim_result
    })

    return {
        "goal": goal,
        "scenario": scenario,
        "learning_patterns": patterns,
        "failures": failures,
        "agents": agent_steps,
        "results": sim_result["results"],
        "best_strategy": best,
        "alternative_strategy": second_best,
        "explanation": explanation,
        "debates": debates,
        "world": world,
        "domain": domain
    }

@app.post("/chat")
async def chat(data: ConversationRequest):
    message = data.message.strip()

    if not message:
        return {"error": "Message is required"}

    intent = conversation_engine.detect_intent(message)

    if conversation_engine.needs_clarification(message):
        return {
            "type": "clarification",
            "intent": intent,
            "response": conversation_engine.build_clarification_question(intent)
        }

    goal = conversation_engine.extract_goal(message)

    # Reuse your simulation system
    scenario = {
        "goal": goal,
        "risk_tolerance": 0.5,
        "budget": 10000,
        "market": "normal"
    }

    sim_result = simulation_engine.run_simulation(goal, scenario)

    domain = world_engine.detect_domain(goal)
    world = world_engine.build_world(domain)

    world["risk_tolerance"] = scenario["risk_tolerance"]
    world["budget"] = scenario["budget"]
    world["market"] = scenario["market"]

    sim_result["results"] = world_engine.apply_world(
        sim_result.get("results", []), world
    )

    debated_strategies, debates = debate_engine.run_debate(
        sim_result["results"], goal
    )
    sim_result["results"] = debated_strategies

    failures = failure_engine.predict(
        sim_result["results"],
        scenario,
        world
    )

    for s in sim_result["results"]:
        if "final_score" not in s:
            s["final_score"] = s.get("score", 0)

        failure_data = next(
            (f for f in failures if f["strategy"] == s["name"]),
            None
        )

        failure_prob = (
            failure_data["failure_probability"] / 100
            if failure_data else 0.3
        )

        base_conf = s.get("confidence", 0.7)
        adjusted_conf = base_conf * (1 - failure_prob)
        trust_score = adjusted_conf * s.get("final_score", 1)

        s["confidence_score"] = round(adjusted_conf * 100, 2)
        s["trust_score"] = round(trust_score, 2)
        s["failure_probability"] = round(failure_prob * 100, 2)
        s["decision_score"] = round(
            s.get("final_score", 0) - (failure_prob * 5),
            2
        )

    sim_result["results"] = sorted(
        sim_result["results"],
        key=lambda x: x["decision_score"],
        reverse=True
    )

    best = sim_result["results"][0]

    explanation = explanation_engine.generate(
        best,
        sim_result["results"],
        failures=failures,
        world=world
    )

    conversational = conversation_engine.build_conversational_response(
        goal,
        best,
        explanation
    )

    return {
        "type": "conversation",
        "intent": intent,
        "goal": goal,
        "response": conversational,
        "best_strategy": best,
        "explanation": explanation
    }

@app.post("/system/run_stream")
async def run_stream(data: SimulationRequest):
    async def event_generator():
        async for step in cognitive_loop.run_simulation_stream(data.dict()):
            yield step

    return StreamingResponse(
        event_generator(),
        media_type="text/plain"
    )


@app.post("/control/approve")
async def approve():
    control_engine.approve()
    return {"status": "approved"}


@app.post("/control/reject")
async def reject():
    control_engine.reject()
    return {"status": "rejected"}


@app.get("/dashboard")
async def dashboard():
    username = "test_user"
    history = await history_engine.get(username)

    total_runs = len(history)
    scores = [
        h["result"]["best_strategy"].get("final_score", 0)
        for h in history if "best_strategy" in h["result"]
    ]
    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "total_runs": total_runs,
        "average_score": avg_score,
        "history": history
    }


@app.get("/lab/history")
async def get_history():
    return await history_engine.get("test_user")


@app.get("/")
def root():
    return {"message": "AURA AI v2 REAL BACKEND 🚀"}


@app.get("/cors-test")
def cors_test():
    return {"status": "ok"}