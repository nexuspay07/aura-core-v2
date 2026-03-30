# app/core/resource_intelligence_engine.py

import psutil
import time


class ResourceIntelligenceEngine:

    def __init__(self):

        self.start_time = time.time()

        self.resource_limits = {
            "cpu": 90,        # percent
            "memory": 90,     # percent
            "time": 5         # seconds per loop
        }

        print("[RESOURCE ENGINE] Initialized")

    def get_current_resources(self):

        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent

        elapsed_time = time.time() - self.start_time

        resources = {
            "cpu": cpu_usage,
            "memory": memory_usage,
            "time": elapsed_time
        }

        print(f"[RESOURCE ENGINE] Current resources: {resources}")

        return resources

    def check_limits(self):

        resources = self.get_current_resources()

        warnings = []

        if resources["cpu"] > self.resource_limits["cpu"]:
            warnings.append("CPU usage too high")

        if resources["memory"] > self.resource_limits["memory"]:
            warnings.append("Memory usage too high")

        if resources["time"] > self.resource_limits["time"]:
            warnings.append("Execution time exceeded")

        if warnings:
            print("[RESOURCE ENGINE] Warnings:", warnings)

        return warnings

    def evaluate_plan_cost(self, plan):

        cost = len(plan)

        print(f"[RESOURCE ENGINE] Estimated plan cost: {cost}")

        return cost


# Singleton
resource_intelligence_engine = ResourceIntelligenceEngine()