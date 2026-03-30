# app/lab/simulation_engine.py

import random


class SimulationEngine:

    def run_simulation(self, goal, scenario):
        risk = scenario.get("risk_tolerance", 0.5)
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")

        # =============================
        # 🎯 BASE STRATEGIES
        # =============================
        strategies = [
            {
                "name": "Aggressive",
                "score": 1.0,
                "risk": "high",
                "confidence": 0.9
            },
            {
                "name": "Balanced",
                "score": 1.0,
                "risk": "medium",
                "confidence": 0.85
            },
            {
                "name": "Conservative",
                "score": 1.0,
                "risk": "low",
                "confidence": 0.8
            },
        ]

        for strat in strategies:

            # =============================
            # 💰 BUDGET IMPACT
            # =============================
            if strat["name"] == "Aggressive":
                strat["score"] += (budget / 10000) * 0.3
            elif strat["name"] == "Balanced":
                strat["score"] += (budget / 15000) * 0.2
            elif strat["name"] == "Conservative":
                strat["score"] += (budget / 20000) * 0.1

            # =============================
            # ⚠️ RISK TOLERANCE IMPACT
            # =============================
            if strat["name"] == "Aggressive":
                strat["score"] += risk * 0.5
            elif strat["name"] == "Balanced":
                strat["score"] += risk * 0.2
            elif strat["name"] == "Conservative":
                strat["score"] += (1 - risk) * 0.4

            # =============================
            # 📈 MARKET CONDITIONS
            # =============================
            if market == "competitive":
                if strat["name"] == "Aggressive":
                    strat["score"] += 0.3
                elif strat["name"] == "Balanced":
                    strat["score"] += 0.2

            elif market == "monopoly":
                if strat["name"] == "Conservative":
                    strat["score"] += 0.4

            # =============================
            # 🎲 RANDOM VARIATION
            # =============================
            strat["score"] += random.uniform(-0.1, 0.1)

            # =============================
            # 🎯 CONFIDENCE ADJUSTMENT
            # =============================
            strat["confidence"] += random.uniform(-0.05, 0.05)
            strat["confidence"] = max(0.5, min(1.0, strat["confidence"]))

        return {"results": strategies}


# ✅ instance
simulation_engine = SimulationEngine()