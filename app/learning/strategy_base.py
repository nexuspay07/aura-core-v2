# app/learning/strategy_base.py

class BaseStrategy:
    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self.fitness = 0.0

    def evaluate_fitness(self, environment_data=None):
        # Placeholder: fitness calculation logic
        # Example: sum of parameter values normalized
        self.fitness = sum(self.params.values()) / max(1, len(self.params))
        return self.fitness

    def execute(self):
        # Placeholder for strategy execution logic
        # Return some dummy result
        return {"strategy": self.name, "result": self.fitness}

# app/learning/strategy_base.py

class StrategyBase:
    def __init__(self, name, parameters=None):
        self.name = name
        self.parameters = parameters or {}

    def execute(self, context=None):
        """
        Override this in child classes.
        context: optional dictionary of environment data
        """
        raise NotImplementedError("Strategy must implement execute()")