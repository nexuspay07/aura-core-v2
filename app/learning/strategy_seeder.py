from app.learning.strategy_registry import add_strategy

def seed_strategies():
    strategies = [
        {"name": "strategy_01", "fitness": 0.5},
        {"name": "strategy_02", "fitness": 0.5},
        {"name": "strategy_03", "fitness": 0.5},
        {"name": "strategy_04", "fitness": 0.5},
        {"name": "strategy_05", "fitness": 0.5},
    ]
    for s in strategies:
        add_strategy(s)
    print(f"[STRATEGY SEEDER] Seeded {len(strategies)} strategies successfully.")

# AUTO-SEED on import (for Uvicorn process)
seed_strategies()