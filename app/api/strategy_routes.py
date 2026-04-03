# app/api/strategy_routes.py

from fastapi import APIRouter
from app.marketplace.strategy_engine import strategy_engine

router = APIRouter(prefix="/strategy", tags=["Strategy Marketplace"])


# ==========================
# SAVE STRATEGY (NO AUTH)
# ==========================
@router.post("/save")
async def save_strategy(data: dict):
    strategy = data.get("strategy")

    if not strategy:
        return {"error": "No strategy provided"}

    # ✅ use guest user
    username = "guest"

    saved = strategy_engine.save_strategy(
        username,
        strategy
    )

    return {"message": "Strategy saved", "strategy": saved}


# ==========================
# GET ALL STRATEGIES
# ==========================
@router.get("/all")
async def get_strategies():
    return strategy_engine.get_all()


# ==========================
# USE STRATEGY
# ==========================
@router.post("/use/{strategy_id}")
async def use_strategy(strategy_id: int):
    strategy = strategy_engine.use_strategy(strategy_id)

    if not strategy:
        return {"error": "Strategy not found"}

    return strategy


# ==========================
# RATE STRATEGY
# ==========================
@router.post("/rate/{strategy_id}")
async def rate_strategy(strategy_id: int, score: int):
    strategy = strategy_engine.rate_strategy(strategy_id, score)

    if not strategy:
        return {"error": "Strategy not found"}

    return strategy