# app/learning/strategy_simulation_engine.py

from app.learning.strategy_registry import get_all_strategies
from app.learning.strategy_base import StrategyBase
from app.persistence.persistence_engine import save_simulation_results

# app/learning/strategy_simulation_engine.py

from app.learning.strategy_registry import strategy_registry

# app/learning/strategy_simulation_engine.py

from app.learning.strategy_registry import strategy_registry
import random

def run_simulation():
    """
    Phase 1 simulation: Run all registered strategies and assign a random score.
    Returns a list of dicts with strategy names and scores.
    """
    results = []
    for strategy in strategy_registry.get_all_strategies():
        score = round(random.uniform(0, 1), 3)  # Random score for demo
        results.append({
            "strategy": strategy.name,
            "score": score
        })
    return results

