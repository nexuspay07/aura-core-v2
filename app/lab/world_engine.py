# app/lab/world_engine.py

import random


class WorldEngine:

    def detect_domain(self, goal):
        if not goal:
            return "general"

        goal = goal.lower()

        # BUSINESS
        if any(word in goal for word in [
            "business", "grow", "startup", "company", "sales", "revenue"
        ]):
            return "business"

        # FINANCE
        if any(word in goal for word in [
            "invest", "stock", "crypto", "trading", "portfolio"
        ]):
            return "finance"

        # HEALTH
        if any(word in goal for word in [
            "health", "fitness", "diet", "exercise"
        ]):
            return "health"

        return "general"

    def build_world(self, domain):

        if domain == "business":
            return {
                "market_growth": random.uniform(0.3, 1.0),
                "competition": random.uniform(0.2, 0.9),
                "risk_level": random.uniform(0.1, 0.9)
            }

        elif domain == "finance":
            return {
                "volatility": random.uniform(0.2, 1.0),
                "interest_rate": random.uniform(0.01, 0.1),
                "risk_level": random.uniform(0.2, 0.9)
            }

        return {
            "uncertainty": random.uniform(0.2, 0.8),
            "risk_level": random.uniform(0.2, 0.8)
        }

    def apply_world(self, strategies, world):

        risk = world.get("risk_level", 0.5)
        competition = world.get("competition", 0.5)
        growth = world.get("market_growth", 0.5)

        for strat in strategies:

            # RISK
            if strat["name"] == "Aggressive":
                strat["score"] -= risk * 0.8

            elif strat["name"] == "Balanced":
                strat["score"] += (1 - risk) * 0.3

            elif strat["name"] == "Conservative":
                strat["score"] += (1 - risk) * 0.6

            # COMPETITION
            if strat["name"] == "Aggressive":
                strat["score"] += competition * 0.5

            elif strat["name"] == "Conservative":
                strat["score"] -= competition * 0.3

            # GROWTH
            if strat["name"] == "Aggressive":
                strat["score"] += growth * 0.6

            elif strat["name"] == "Balanced":
                strat["score"] += growth * 0.4

            elif strat["name"] == "Conservative":
                strat["score"] += growth * 0.2

        return strategies


world_engine = WorldEngine()