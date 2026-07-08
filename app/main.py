from app.memory.memory_service import (
    save_memory
)

from app.memory.memory_retriever import (
    retrieve_relevant_memories
)

from app.db.business_profile_table import (
    business_profile_table
)


from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import (
    Base,
    engine
)

from app.models.strategy import strategies
from app.models.simulation import simulations
from app.models.strategy import metadata as strategy_metadata
from app.core.output_standardization_engine import (
    output_standardization_engine
)


Base.metadata.create_all(bind=engine)
strategy_metadata.create_all(bind=engine)

app = FastAPI(title="AURA AI")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "https://aura-business-frontend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# IMPORTS
# =========================
from app.db.database import engine, metadata

from app.lab.world_engine import world_engine
from app.lab.history_engine import history_engine
from app.lab.learning_engine import learning_engine
from app.lab.failure_engine import failure_engine
from app.lab.simulation_engine import simulation_engine
from app.lab.explanation_engine import explanation_engine
from app.lab.agent_engine import agent_engine
from app.lab.debate_engine import debate_engine
from app.db.user_table import user_table
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.core.conversation_memory import conversation_memory
from app.core.decision_memory_engine import decision_memory_engine
from app.core.agents.multi_agent_engine import multi_agent_engine

from app.core.cognitive_loop import cognitive_loop
from app.control.control_engine import control_engine

from app.api.strategy_routes import router as strategy_router
from app.api.marketplace_routes import router as marketplace_router
from app.core.strategic_evolution_engine import strategic_evolution_engine
from app.api.pro_routes import router as pro_router
from app.api.payment_routes import router as payment_router

from app.core.memory.conversation_engine import conversation_engine

from app.core.user_profile_engine import user_profile_engine

from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.healthcare.healthcare_engine import healthcare_engine
from app.db.decision_memory_table import decision_memory_table
from app.db.organization_table import organization_table
from app.db.workspace_table import workspace_table
from app.api.organization_routes import router as organization_router
from app.db.intelligence_session_table import intelligence_session_table
from sqlalchemy import select, insert
from app.db.organization_table import organization_table
from app.db.workspace_table import workspace_table
from app.db.intelligence_session_table import intelligence_session_table
from app.api.intelligence_session_routes import router as intelligence_session_router

from app.core.simulation.prediction_engine import prediction_engine
from app.core.uncertainty_engine import uncertainty_engine
from app.core.adaptive_learning_v2_engine import adaptive_learning_v2_engine
from app.core.strategy_reinforcement_engine import strategy_reinforcement_engine
from app.core.reasoning.causal_reasoning_engine import causal_reasoning_engine
from app.services.memory_service import (
    save_user_memory,
    get_user_memories,
    save_organization_memory,
    get_organization_memories,
    save_session_memory,
    get_session_memory,
)

app.include_router(chat_router)
app.include_router(payment_router)
app.include_router(pro_router)
app.include_router(strategy_router)
app.include_router(marketplace_router)
app.include_router(organization_router)
app.include_router(intelligence_session_router)
app.include_router(auth_router)


# =========================
# HELPERS
# =========================
def generate_action_plan(strategy):
    name = strategy.get("name", "Balanced")

    if name == "Aggressive":
        return [
            "Launch MVP immediately",
            "Invest heavily in user acquisition",
            "Scale rapidly"
        ]

    elif name == "Balanced":
        return [
            "Validate product-market fit",
            "Scale gradually",
            "Optimize operations"
        ]

    return [
        "Minimize costs",
        "Run small experiments",
        "Grow steadily"
    ]


def add_prediction_and_uncertainty(results, world):
    predictions = prediction_engine.simulate_multiple(results, world)
    ranked_predictions = uncertainty_engine.enrich_predictions(predictions)

    prediction_map = {p["strategy"]: p for p in ranked_predictions}

    for s in results:
        name = s.get("name")

        if name in prediction_map:
            p = prediction_map[name]
            s["prediction"] = p
            s["predicted_score"] = p.get("predicted_score")
            s["prediction_probability"] = p.get("probability")
            s["expected_value"] = p.get("expected_value")
            s["uncertainty_risk"] = p.get("uncertainty_risk")
            s["prediction_range"] = p.get("prediction_range")

    return results


def add_strategy_enrichment(results, failures):
    for s in results:
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

        predicted_score = s.get("predicted_score", s.get("final_score", 0))
        expected_value = s.get("expected_value", predicted_score)
        uncertainty_risk = s.get("uncertainty_risk", 0.3)

        decision_score = (
            (s.get("final_score", 0) * 0.35) +
            (predicted_score * 0.30) +
            (expected_value * 0.20) +
            (trust_score * 0.15)
        ) - ((failure_prob * 5) + (uncertainty_risk * 2))

        s["decision_score"] = round(decision_score, 2)

        s["outcome"] = {
            "reward": "high" if s.get("score", 0) > 2 else "medium",
            "risk": s.get("risk", "unknown"),
            "timeframe": "short-term" if s.get("risk") == "high" else "long-term"
        }

    return sorted(results, key=lambda x: x["decision_score"], reverse=True)


def is_healthcare_message(message: str) -> bool:
    keywords = [
        "pain", "fever", "cough", "headache", "fatigue",
        "dizziness", "shortness of breath", "chest pain",
        "symptom", "medical", "health"
    ]

    return any(k in message.lower() for k in keywords)

async def auto_save_intelligence_session(
    organization_id: int | None,
    workspace_id: int | None,
    session_id: str,
    goal: str,
    response: dict,
    pipeline_result: dict
):
    if not organization_id or not workspace_id:
        return None

    org = await database.fetch_one(
        select(organization_table).where(
            organization_table.c.id == organization_id
        )
    )

    if not org:
        return None

    workspace = await database.fetch_one(
        select(workspace_table).where(
            workspace_table.c.id == workspace_id
        )
    )

    if not workspace:
        return None

    if workspace["organization_id"] != organization_id:
        return None

    decision_brief = response.get("decision_brief", {})
    business_dna = pipeline_result.get("business_dna", {})

    title = goal[:80]

    query = insert(intelligence_session_table).values(
        organization_id=organization_id,
        workspace_id=workspace_id,
        created_by_user_id=org["owner_user_id"],
        title=title,
        goal=goal,
        domain="business",
        session_type="decision_analysis",
        status="completed",
        summary=response.get("summary"),
        recommended_move=decision_brief.get("recommended_move"),
        risk_level=response.get("risk_profile"),
        business_model=business_dna.get("business_model"),
        is_active=True,
    )

    saved_id = await database.execute(query)

    return {
        "saved": True,
        "intelligence_session_id": saved_id,
        "organization_id": organization_id,
        "workspace_id": workspace_id
    }

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "system": "AURA CORE",
        "state": "running"
    }


# =========================
# STARTUP / SHUTDOWN
# =========================
@app.on_event("startup")
async def startup():
    metadata.create_all(engine)



@app.on_event("shutdown")
async def shutdown():
 pass
          


# =========================
# MODELS
# =========================

class SimulationRequest(BaseModel):
    goal: str
    risk_tolerance: float = 0.5
    budget: int = 10000
    market: str = "normal"


class ConversationRequest(BaseModel):
    message: str
    session_id: str | None = None
    organization_id: int | None = None
    workspace_id: int | None = None


# =========================
# LAB SIMULATION
# =========================
@app.post("/lab/simulate")
async def simulate(data: SimulationRequest):
    scenario = data.dict()
    goal = scenario.get("goal", "").strip()

    if not goal:
        return {"error": "Goal is required"}

    username = "test_user"

    sim_result = simulation_engine.run_simulation(goal, scenario)

    world = world_engine.build_world("business")
    world.update(scenario)

    world = causal_reasoning_engine.analyze_causality(
        world,
        context={},
        memories=[]
    )

    sim_result["results"] = world_engine.apply_world(
        sim_result.get("results", []),
        world
    )

    sim_result["results"] = add_prediction_and_uncertainty(
        sim_result["results"],
        world
    )

    patterns = await learning_engine.learn(username, history_engine)

    sim_result["results"] = learning_engine.apply_learning(
        sim_result["results"],
        scenario,
        patterns
    )

    debated_strategies, debates = debate_engine.run_debate(
        sim_result["results"],
        goal
    )

    sim_result["results"] = debated_strategies

    agent_steps = agent_engine.run_agents(sim_result)

    failures = failure_engine.predict(sim_result["results"], scenario, world)

    sim_result["results"] = add_strategy_enrichment(
        sim_result["results"],
        failures
    )

    best = sim_result["results"][0]
    best["action_plan"] = generate_action_plan(best)

    second_best = sim_result["results"][1] if len(sim_result["results"]) > 1 else None

    if second_best:
        second_best["action_plan"] = generate_action_plan(second_best)

    explanation = explanation_engine.generate(
        best,
        sim_result["results"],
        failures=failures,
        world=world
    )

    await history_engine.save(
        username,
        {
            "goal": goal,
            "scenario": scenario,
            "result": {
                "results": sim_result["results"],
                "best_strategy": best
            }
        }
    )

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
        "domain": "business"
    }


# =========================
# STREAM
# =========================
@app.post("/system/run_stream")
async def run_stream(data: SimulationRequest):
    async def event_generator():
        async for step in cognitive_loop.run_simulation_stream(data.dict()):
            yield step

    return StreamingResponse(event_generator(), media_type="text/plain")


# =========================
# CONTROL
# =========================
@app.post("/control/approve")
async def approve():
    control_engine.approve()
    return {"status": "approved"}


@app.post("/control/reject")
async def reject():
    control_engine.reject()
    return {"status": "rejected"}


# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
async def dashboard():
    username = "test_user"
    history = await history_engine.get(username)

    total_runs = len(history)

    scores = [
        h["result"]["best_strategy"].get("final_score", 0)
        for h in history
        if "result" in h and "best_strategy" in h["result"]
    ]

    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "total_runs": total_runs,
        "average_score": avg_score,
        "history": history
    }


# =========================
# HISTORY
# =========================
@app.get("/lab/history")
async def get_history():
    return await history_engine.get("test_user")


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"message": "AURA AI RUNNING 🚀"}


@app.get("/cors-test")
def cors_test():
    return {"status": "ok"}

@app.get("/routes")
async def routes_debug():
    return {
        "routes": [
            str(route.path)
            for route in app.routes
        ]
    }