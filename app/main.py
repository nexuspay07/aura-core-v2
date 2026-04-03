import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ==========================
# CREATE APP
# ==========================
app = FastAPI(title="AURA AI")

# ==========================
# ✅ CORS (FIXED)
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # keep for now (safe to tighten later)
        "http://localhost:3000",
        "https://aura-frontend-tmsb.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# DATABASE
# ==========================
from app.db.database import database, engine, metadata

# ==========================
# CORE SYSTEMS
# ==========================
from app.lab.world_engine import world_engine
from app.lab.history_engine import history_engine
from app.core.cognitive_loop import cognitive_loop
from app.control.control_engine import control_engine
from app.lab.simulation_engine import simulation_engine
from app.lab.explanation_engine import explanation_engine
from app.lab.agent_engine import agent_engine
from app.lab.debate_engine import debate_engine

# ==========================
# ROUTERS
# ==========================
from app.api.strategy_routes import router as strategy_router
from app.routes import simulation
from app.api.marketplace_routes import router as marketplace_router

app.include_router(strategy_router)
app.include_router(simulation.router)
app.include_router(marketplace_router)

# ==========================
# STARTUP / SHUTDOWN
# ==========================
@app.on_event("startup")
async def startup():
    metadata.create_all(engine)
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ==========================
# REQUEST MODEL
# ==========================
class SimulationRequest(BaseModel):
    goal: str
    risk_tolerance: float = 0.5
    budget: int = 10000
    market: str = "normal"

# ==========================
# SAFE USER (NO LOGIN MODE)
# ==========================
async def get_optional_user():
    return {"username": "guest"}

# ==========================
# SIMULATION
# ==========================
@app.post("/lab/simulate")
async def simulate(
    data: SimulationRequest,
    current_user: dict = Depends(get_optional_user)
):
    scenario = data.dict()
    goal = scenario.get("goal")

    if not goal or goal.strip() == "":
        return {"error": "Goal is required"}

    username = current_user["username"]

    sim_result = simulation_engine.run_simulation(goal, scenario)

    domain = world_engine.detect_domain(goal)
    world = world_engine.build_world(domain)

    world.update({
        "risk_tolerance": scenario["risk_tolerance"],
        "budget": scenario["budget"],
        "market": scenario["market"],
    })

    sim_result["results"] = world_engine.apply_world(
        sim_result.get("results", []), world
    )

    patterns = await history_engine.analyze_patterns(username)

    for strategy in sim_result["results"]:
        if strategy["name"] in patterns:
            strategy["score"] += patterns[strategy["name"]] * 0.2

    debated_strategies, debates = debate_engine.run_debate(
        sim_result["results"], goal
    )
    sim_result["results"] = debated_strategies

    agent_steps = agent_engine.run_agents(sim_result)

    for s in sim_result["results"]:
        if "final_score" not in s:
            s["final_score"] = s.get("score", 0)

    sim_result["results"] = sorted(
        sim_result["results"],
        key=lambda x: x["final_score"],
        reverse=True
    )

    best = sim_result["results"][0] if sim_result["results"] else {}

    explanation = explanation_engine.generate({
        "results": sim_result["results"],
        "best_strategy": best
    })

    await history_engine.save(username, {
        "goal": goal,
        "scenario": scenario,
        "result": sim_result
    })

    return {
        "goal": goal,
        "scenario": scenario,
        "agents": agent_steps,
        "results": sim_result["results"],
        "best_strategy": best,
        "explanation": explanation,
        "debates": debates,
        "memory_patterns": patterns,
        "world": world,
        "domain": domain
    }

# ==========================
# STREAM (FIXED)
# ==========================
@app.post("/system/run_stream")
async def run_stream(
    data: SimulationRequest,
    current_user: dict = Depends(get_optional_user)
):
    async def event_generator():
        try:
            async for step in cognitive_loop.run_simulation_stream(data.dict()):
                yield f"{step}\n"
        except Exception as e:
            yield f"❌ Stream error: {str(e)}\n"

    return StreamingResponse(event_generator(), media_type="text/plain")

# ==========================
# CONTROL
# ==========================
@app.post("/control/approve")
async def approve():
    control_engine.approve()
    return {"status": "approved"}

@app.post("/control/reject")
async def reject():
    control_engine.reject()
    return {"status": "rejected"}

# ==========================
# DASHBOARD
# ==========================
@app.get("/dashboard")
async def dashboard(current_user: dict = Depends(get_optional_user)):
    username = current_user["username"]

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

# ==========================
# HISTORY
# ==========================
@app.get("/lab/history")
async def get_history(current_user: dict = Depends(get_optional_user)):
    return await history_engine.get(current_user["username"])

# ==========================
# ROOT
# ==========================
@app.get("/")
def root():
    return {"message": "AURA AI running 🚀"}

# ==========================
# TEST
# ==========================
@app.get("/cors-test")
def cors_test():
    return {"status": "ok"}