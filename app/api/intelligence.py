from fastapi import APIRouter
from app.learning.strategy_memory_engine import StrategyMemoryEngine
from app.learning.strategy_darwin_engine import StrategyDarwinEngine

router = APIRouter()


@router.get("/strategies/ranking")
def get_strategy_ranking():
    """
    Return ranked strategies based on historical performance.
    """

    memory_engine = StrategyMemoryEngine()

    ranking = memory_engine.get_strategy_ranking()

    return {
        "status": "success",
        "strategy_ranking": ranking
    }


@router.get("/strategies/best")
def get_best_strategy():
    """
    Return best performing strategy.
    """

    darwin = StrategyDarwinEngine()

    best = darwin.select_best_strategy()

    return {
        "status": "success",
        "best_strategy": best
    }