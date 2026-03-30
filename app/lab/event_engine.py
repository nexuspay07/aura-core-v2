import time


class EventEngine:

    def generate_events(self, simulation_result):
        events = []

        events.append("Initializing simulation...")
        events.append("Loading strategies...")
        events.append("Executing simulations...")
        events.append("Analyzing results...")

        best = simulation_result["best_strategy"]["name"]

        events.append(f"Best strategy selected: {best}")
        events.append("Simulation complete.")

        return events


# ✅ instance
event_engine = EventEngine()