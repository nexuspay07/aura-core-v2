# app/learning/strategy_model.py

class Strategy:

    def __init__(self, strategy_id, name, parent=None, mutation_rate=0.0):
        self.strategy_id = strategy_id
        self.name = name
        self.parent = parent
        self.mutation_rate = mutation_rate

    def to_dict(self):
        return {
            "id": self.strategy_id,
            "name": self.name,
            "parent": self.parent,
            "mutation_rate": self.mutation_rate
        }

    def __repr__(self):
        return f"<Strategy {self.strategy_id}: {self.name}>"