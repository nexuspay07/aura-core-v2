# app/learning/strategy_registry.py

class Strategy:
    def __init__(self, strategy_id, name, parameters=None):
        self.strategy_id = strategy_id
        self.name = name
        self.parameters = parameters or {}

class StrategyRegistry:
    def __init__(self):
        self.strategies = []

        # Default strategies
        self.register_strategy(Strategy(1, "Exploration Strategy", {"risk": 0.8}))
        self.register_strategy(Strategy(2, "Efficiency Strategy", {"speed": 0.9}))
        self.register_strategy(Strategy(3, "Balanced Strategy", {"balance": 0.5}))

        print("[STRATEGY REGISTRY] Initialized with default strategies")

    def register_strategy(self, strategy):
        self.strategies.append(strategy)
        print(f"[STRATEGY REGISTRY] Strategy registered: {strategy.strategy_id}")

    def get_strategy(self, strategy_id):
        for s in self.strategies:
            if s.strategy_id == strategy_id:
                return s
        return None

    def get_all_strategies(self):
        return self.strategies

# -------------------------
# Singleton instance for global access
strategy_registry = StrategyRegistry()

# -------------------------
# Convenience function for API
def get_all_strategies():
    return strategy_registry.get_all_strategies()