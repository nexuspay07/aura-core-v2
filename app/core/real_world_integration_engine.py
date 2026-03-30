# app/core/real_world_integration_engine.py

import random
import time


class RealWorldIntegrationEngine:
    """
    Phase 213 — Real World Data Integration
    Connects AURA to external data sources such as:
    APIs, IoT sensors, databases, and market feeds
    """

    def __init__(self):
        self.sources = []

    def register_source(self, name, source_type):
        """
        Register external data source
        """
        self.sources.append({
            "name": name,
            "type": source_type
        })

        print(f"[REAL WORLD INTEGRATION] Source registered: {name}")

    def collect_data(self):
        """
        Collect data from all registered sources
        """

        collected = {}

        for source in self.sources:

            # Mock sensor/API data for now
            collected[source["name"]] = {
                "type": source["type"],
                "timestamp": time.time(),
                "value": random.randint(1, 100)
            }

        if collected:
            print("[REAL WORLD INTEGRATION] Data collected")

        return collected


# Global engine instance
real_world_integration_engine = RealWorldIntegrationEngine()


# Example default sources (can remove later)
real_world_integration_engine.register_source("traffic_sensors", "iot")
real_world_integration_engine.register_source("energy_grid", "iot")
real_world_integration_engine.register_source("market_feed", "api")