# app/api/strategy_routes.py

from fastapi import APIRouter, Depends
from app.routes.auth import get_current_user
from app.marketplace.strategy_engine import strategy_engine

router = APIRouter(prefix="/strategy", tags=["Strategy Marketplace"])


@router.post("/save")
async def save_strategy(data: dict, current_user=Depends(get_current_user)):
    strategy = data.get("strategy")

    if not strategy:
        return {"error": "No strategy provided"}

    saved = strategy_engine.save_strategy(
        current_user["username"],
        strategy
    )

    return {"message": "Strategy saved", "strategy": saved}


@router.get("/all")
async def get_strategies():
    return strategy_engine.get_all()


@router.post("/use/{strategy_id}")
async def use_strategy(strategy_id: int):
    strategy = strategy_engine.use_strategy(strategy_id)

    if not strategy:
        return {"error": "Strategy not found"}

    return strategy


@router.post("/rate/{strategy_id}")
async def rate_strategy(strategy_id: int, score: int):
    strategy = strategy_engine.rate_strategy(strategy_id, score)

    if not strategy:
        return {"error": "Strategy not found"}

    return strategy