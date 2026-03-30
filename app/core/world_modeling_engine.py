# app/core/world_modeling_engine.py

class WorldModelingEngine:

    def __init__(self):
        self.models = {}
        print("[WORLD MODELING ENGINE] Initialized")

    def create_model(self, name, variables, relationships):
        """Create a system model with variables and relationships."""
        self.models[name] = {
            "variables": variables,
            "relationships": relationships
        }
        print(f"[WORLD MODEL] Created: {name}")

    def get_model(self, name):
        """Retrieve a model by name."""
        return self.models.get(name)

    def update_model(self, name, updates):
        """Update model variables."""
        if name in self.models:
            self.models[name]["variables"].update(updates)
            print(f"[WORLD MODEL] Updated: {name}")

    def simulate_outcome(self, name, changes):
        """Simulate variable changes and return predicted state."""
        model = self.models.get(name)
        if not model:
            print(f"[WORLD MODEL] Model '{name}' not found")
            return None

        # Copy current state
        state = model["variables"].copy()

        # Apply changes
        for variable, change in changes.items():
            if variable in state:
                state[variable] += change

        print(f"[WORLD MODEL] Simulation executed for {name}")
        return state


# Global instance
world_modeling_engine = WorldModelingEngine()