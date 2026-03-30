from fastapi import APIRouter, HTTPException
from app.learning.strategy_registry import get_strategies, clear_strategies
from app.learning.strategy_seeder import seed_strategies
from app.learning.strategy_evolution_engine import strategy_evolution_engine
from app.core.system_decision import execute_decision

router = APIRouter()

# 1️⃣ Seed / Reset Strategies
@router.post("/seed", summary="Seed new strategies")
def seed_system_strategies():
    clear_strategies()
    seed_strategies()
    strategies = get_strategies()
    return {"status": "strategies_seeded", "total": len(strategies)}

# 2️⃣ Execute a decision
@router.post("/run", summary="Execute a system decision")
def run_system_decision():
    result = execute_decision()
    return result

# 3️⃣ Evolve a specific strategy
@router.post("/evolve/{strategy_name}", summary="Evolve a strategy")
def evolve_strategy_route(strategy_name: str):
    strategies = get_strategies()
    strategy = next((s for s in strategies if s["name"] == strategy_name), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="strategy_not_found")
    
    evolved = strategy_evolution_engine.evolve_strategy(strategy)
    return {"status": "strategy_evolved", "strategy": evolved}

# 4️⃣ Get all strategies
@router.get("/strategies", summary="List all strategies")
def list_strategies():
    strategies = get_strategies()
    return {"total": len(strategies), "strategies": strategies}

# app/api/system.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter()

@router.get("/run_stream")
async def run_system_stream():
    async def event_generator():
        for i in range(10):
            yield f"data: Step {i}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")