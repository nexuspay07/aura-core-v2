# system_decision.py
from app.learning.strategy_registry import get_strategies
from app.learning.strategy_evolution_engine import strategy_evolution_engine

def execute_decision():
    strategies = get_strategies()
    if not strategies:
        print("[SYSTEM DECISION] No strategies available!")
        return {"status": "no_strategies_available"}

    # Pick first strategy for execution
    strategy = strategies[0]
    print(f"[SYSTEM DECISION] Executing strategy: {strategy['name']}")
    strategy["fitness"] = 0.5
    return {
        "status": "decision_executed",
        "strategy_used": strategy["name"],
        "fitness": strategy["fitness"],
        "total_strategies": len(strategies)
    }

def evolve_used_strategy(strategy_name: str):
    strategies = get_strategies()
    strategy = next((s for s in strategies if s["name"] == strategy_name), None)
    if not strategy:
        return {"status": "strategy_not_found"}
    evolved = strategy_evolution_engine.evolve_strategy(strategy)
    return {"status": "strategy_evolved", "strategy": evolved}